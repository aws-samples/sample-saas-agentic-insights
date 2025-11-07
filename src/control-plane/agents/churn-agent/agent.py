import os
import asyncio
import tempfile
import hashlib
from datetime import datetime
from typing import Optional
import boto3
from strands import Agent, tool
from db_context import get_db_context
from code_context import get_code_context


# ======= STEP 2 =======
# @tool(description="Execute the SQL query and return the result as CSV.")
# async def execute_sql(query: str) -> str:
#     """Execute a SQL query and return the result."""
#     try:
#         db_ctx = get_db_context()
#         return await db_ctx.execute_query(query)
#     except Exception as e:
#         return f"ERROR: {str(e)}"
# ======= STEP 2 =======


# ======= STEP 3 =======
# @tool(
#     description="Execute python code. Alternatively, you can set the keepalive parameter to true, to keep the environment running and prevent automatic garbage collection."
# )
# async def execute_python(code: str = None) -> str:
#     """Execute Python code and return the result."""
#     if not code:
#         return "ERROR: No code provided"
#
#     try:
#         code_ctx = get_code_context()
#         return code_ctx.execute_code(code)
#     except Exception as e:
#         return f"ERROR: {str(e)}"
# ======= STEP 3 =======

# ======= STEP 4 =======
# @tool(description="Executes the SQL query and writes the result to `filename`, potentially overwriting the file.")
# async def load_data(query: str, filename: str) -> str:
#     """Execute SQL query, save as CSV to temp file, and upload to code interpreter."""
#     try:
#         db_ctx = get_db_context()
#         result = await db_ctx.execute_query(query)
#
#         # Check if result is an error
#         if result.startswith("SQL Error:"):
#             return result
#
#         # Create temp file and upload to code interpreter
#         with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as temp_file:
#             temp_file.write(result)
#             temp_file_path = temp_file.name
#
#         try:
#             # Upload to code interpreter
#             code_ctx = get_code_context()
#             upload_result = code_ctx.upload_file(filename, result)
#             return f"Query executed and uploaded as '{filename}': {upload_result}"
#         finally:
#             # Clean up temp file
#             os.unlink(temp_file_path)
#
#     except Exception as e:
#         return f"ERROR: {str(e)}"
# ======= STEP 4 =======


@tool(description="Download file from code interpreter, hash it, and upload to S3 with hash as filename")
async def publish_asset(path: str) -> str:
    """Download file from code interpreter and publish to S3 with SHA1 hash filename."""
    try:
        code_ctx = get_code_context()

        # Read file from code interpreter
        response = code_ctx._client.invoke_code_interpreter(
            codeInterpreterIdentifier="aws.codeinterpreter.v1",
            sessionId=code_ctx._session_id,
            name="readFiles",
            arguments={"paths": [path]},
        )

        # Extract file content from response
        file_content = None
        mime_type = None
        for event in response["stream"]:
            if "result" in event and "content" in event["result"]:
                for content_item in event["result"]["content"]:
                    if content_item.get("type") == "resource" and "resource" in content_item:
                        resource = content_item["resource"]
                        if resource.get("uri") == f"file:///{path}":
                            file_content = resource.get("blob")
                            mime_type = resource.get("mimeType")
                            break

        if not file_content:
            return f"ERROR: Could not read file {path}"

        # Generate SHA1 hash
        sha1_hash = hashlib.sha1(file_content).hexdigest()

        # Get file extension
        _, ext = os.path.splitext(path)
        hashed_filename = f"{sha1_hash}{ext}"

        # Upload to S3
        s3_client = boto3.client("s3")
        bucket_name = os.getenv("S3_BUCKET", "churn-agent-assets")

        upload_params = {"Bucket": bucket_name, "Key": hashed_filename, "Body": file_content}

        if mime_type:
            upload_params["ContentType"] = mime_type

        s3_client.put_object(**upload_params)

        s3_url = f"https://{bucket_name}.s3.amazonaws.com/{hashed_filename}"
        return f"Asset published: {s3_url}"

    except Exception as e:
        return f"ERROR: {str(e)}"


# Step 1: Basic system prompt
system_prompt = f"""Today is {datetime.now().strftime('%Y-%m-%d')} (YYYY-MM-DD).

You are the churn agent. Your job is it to analyze large churn datasets together
with business users and help them get insights into the churn patterns of their user base."""

# ======= STEP 2 =======
# system_prompt += """ You have read-only access to a database that you can query using the execute_sql tool.
#
# The database uses the Postgres conventions (but is Aurora DSQL and doesn't support all aggregation operations).
# Then schema is this: CREATE TABLE IF NOT EXISTS churn_data (
#     customer_id INTEGER PRIMARY KEY,
#     signup_date DATE,
#     company_size INTEGER,  -- 0=Startup, 1=Mid-Market, 2=Enterprise
#     contract_type INTEGER, -- 0=Monthly, 1=Annual
#     tier INTEGER,          -- 0=Free, 1=Standard, 2=Premium, 3=Enterprise
#     churn BOOLEAN,
#     churn_date DATE,
#     voluntary_churn BOOLEAN, -- TRUE=voluntary churn, FALSE=involuntary churn (bankruptcy, getting bought), NULL=no churn
#     open_tickets INTEGER,
#     outage_count INTEGER,
#     feature_count INTEGER,
#     csm_touches INTEGER,
#     sla_misses INTEGER,
#     mau INTEGER, -- The monthly active users for last month (for active customers) or the last known value before cancellation (for inactive ones)
#     api_calls INTEGER, -- The number of API calls for last month (for active customers) or the last known value before cancellation (for inactive ones)
#     mau_delta INTEGER, -- The delta between last month and the month before that
#     api_calls_delta INTEGER -- The delta between last month and the month before that
# )"""
# ======= STEP 2 =======

# ======= STEP 3 =======
# system_prompt += """ You can use the execute_python tool to execute
# code to analyze the data. Never peak at more than 20 rows at a time.
#
# IMPORTANT: The user has NO access to the local file system. DO NOT CREATE IMAGES OR OTHER ASSETS AS THE USER
# CAN'T INTERACT WITH THEM.
#
# NEVER TRY TO EXECUTE COMMANDS OR INSTALL MISSING PACKAGES IN THE CODING ENVIRONMENT.
#
# CRITICAL CODE EXECUTION RULES:
# - Code execution is ONLY for data analysis using pandas, numpy, matplotlib, or similar libraries
# - NEVER execute code that consists only of print statements or text output
# - Code must perform actual computations, data transformations, or generate visualizations
# - Do NOT use code execution to echo information back to the user
# - Available libraries: pandas, numpy, matplotlib (NOT seaborn - it's not installed)
# - If you need to show results, return computed values or save visualizations to files"""
# ======= STEP 3 =======

# ======= STEP 4 =======
# system_prompt += """ The database is really large, however, and thus it is not feasible to analyze the dataset in the context
# window. Instead, you can use SQL to "peak" at the data, and then use the `load_data` tool to write
# the results to an interactive python environment."""
# ======= STEP 4 =======

system_prompt += """

It is important that you - as the expert - give the user options and explain what they mean. For example,
the user is asking about time-to-churn for a given tenant. You can model this with a variety of statistical
measures. Ask the user which one to use and explain what each would mean, and their drawbacks, such that
the user can make an informed choice. ASK THE USER AND WAIT FOR EXPLICIT CONFIRMATION. Verify which simulations
you can run by looking at the installed packages of the code interpreter. Then, use the `load_data` 
tool to prepare the environment and run the `execute_python` tool to run the analysis. Your customers can't 
read files, so you need to echo the results of the python execution to them.

Your responses need to be in markdown. DON'T USE HEADINGS in your responses. Answer in complete paragraphs
and never uses lists or bulletpoints, unless explicitly instructed by the user. Keep your answers short and
concise. NEVER USE BULLETPOINTS OR LISTS. If YOU MAKE SUGGESTIONS TO A USER FORMAT THEM AS A PARAGRAPH.

<EXAMPLE>
User: What's the churn rate by tier?
Assistant: 

I can calculate churn rate by tier using three approaches. The first is a simple percentage, calculated as churned_customers divided by total_customers. This method is easy to interpret and gives a quick snapshot of overall customer retention. However, it doesn’t account for signup timing, meaning newer customers haven’t had enough time to churn, which can distort comparisons across cohorts.

The second approach is a time-normalized rate, computed as churned divided by customers_active_for_90days. This provides a fairer comparison across tiers since it standardizes exposure time and focuses on customers who have been active long enough to exhibit stable behavior. The trade-off is that it excludes recently signed-up customers, which can make early churn patterns harder to detect.

The third option is cohort-based survival analysis using Kaplan-Meier curves. This method accounts for censoring and reveals churn timing patterns, allowing us to model the probability of retention over time. The downside is that it is more complex to interpret. 

Which approach would you prefer?

"""


agent = Agent(
    system_prompt=system_prompt,
    tools=[
        # STEP 2: execute_sql,
        # STEP 3: execute_python,
        # STEP 4: load_data,
    ],
    model="global.anthropic.claude-haiku-4-5-20251001-v1:0",
    callback_handler=None,
)

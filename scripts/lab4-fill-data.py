#!/usr/bin/env python3

import numpy as np
import pandas as pd
import json
import sys
import argparse
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import boto3
import psycopg2
from psycopg2.extras import execute_values
from tqdm import tqdm

PERSONALITY_TRAITS = [
    "price_sensitivity",
    "budget_rigidity",
    "reliability_need",
    "feature_completeness_need",
    "ease_of_use_need",
    "integration_need",
    "power_user_propensity",
    "self_sufficiency",
    "adoption_speed",
    "change_aversion",
    "support_dependency",
    "csm_relationship_value",
    "community_engagement",
    "brand_loyalty",
    "competitor_awareness",
    "trust_in_vendor",
    "mission_criticality",
    "company_growth_rate",
    "tech_savviness",
    "security_focus",
]

EVENTS = [
    {
        "type": "PriceIncrease",
        "cat": "Pricing",
        "impact": -5,
        "trigger": "global",
        "date": datetime(2024, 6, 1),
        "trait": "price_sensitivity",
        "update": lambda t: t.update({"open_tickets": t.get("open_tickets", 0) + 1}),
    },
    {
        "type": "MajorOutage",
        "cat": "Product",
        "impact": -10,
        "trigger": "global",
        "date": datetime(2023, 11, 15),
        "trait": "reliability_need",
        "update": lambda t: t.update(
            {"open_tickets": t.get("open_tickets", 0) + 3, "outage_count": t.get("outage_count", 0) + 1}
        ),
    },
    {
        "type": "SlowSupportResponse",
        "cat": "Support",
        "impact": -3,
        "trigger": "prob",
        "prob": 0.03,
        "trait": "support_dependency",
        "update": lambda t: t.update({"open_tickets": t.get("open_tickets", 0) + 1}),
    },
    {
        "type": "HighlyRequestedFeatureLaunch",
        "cat": "Product",
        "impact": 6,
        "trigger": "global",
        "date": datetime(2024, 9, 1),
        "trait": "feature_completeness_need",
        "update": lambda t: t.update({"feature_count": t.get("feature_count", 0) + 1}),
    },
    {
        "type": "ProactiveCSMOutreach",
        "cat": "Support",
        "impact": 3,
        "trigger": "prob",
        "prob": 0.05,
        "trait": "csm_relationship_value",
        "update": lambda t: t.update(
            {"open_tickets": max(0, t.get("open_tickets", 0) - 1), "csm_touches": t.get("csm_touches", 0) + 1}
        ),
    },
    {
        "type": "FreeTierNerfed",
        "cat": "Pricing",
        "impact": -25,
        "trigger": "global",
        "date": datetime(2024, 10, 1),
        "trait": "mission_criticality",
        "update": lambda t: t.update({"open_tickets": t.get("open_tickets", 0) + 2}),
    },
    {
        "type": "EnterpriseSupportSLA_Miss",
        "cat": "Support",
        "impact": -35,
        "trigger": "prob",
        "prob": 0.02,
        "trait": "support_dependency",
        "update": lambda t: t.update(
            {"open_tickets": t.get("open_tickets", 0) + 2, "sla_misses": t.get("sla_misses", 0) + 1}
        ),
    },
    {
        "type": "SupportTicketResolved",
        "cat": "Support",
        "impact": 5,
        "trigger": "prob",
        "prob": 0.1,
        "trait": "support_dependency",
        "update": lambda t: (
            t.update({"open_tickets": max(0, t.get("open_tickets", 0) - 1)}) if t.get("open_tickets", 0) > 0 else None
        ),
    },
    {
        "type": "Acquisition",
        "cat": "External",
        "impact": -100,
        "trigger": "prob",
        "prob": 0.001,
        "update": lambda t: None,
    },
    {
        "type": "GoesOutOfBusiness",
        "cat": "External",
        "impact": -100,
        "trigger": "prob",
        "prob": 0.002,
        "update": lambda t: None,
    },
]


def parse_args():
    parser = argparse.ArgumentParser(description="Generate and load churn data to Aurora DSQL")
    parser.add_argument("--num-tenants", type=int, default=5000, help="Number of tenants to generate")
    parser.add_argument("--end", type=str, default=datetime.today().strftime("%Y-%m-%d"), help="Snapshot date (YYYY-MM-DD)")
    parser.add_argument("--churn-threshold", type=float, default=40.0, help="Satisfaction threshold below which customers churn")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument('--cluster-id', type=str, required=True, help='Aurora DSQL cluster ID')
    parser.add_argument('--region', type=str, default='us-east-1', help='AWS region')
    parser.add_argument('--database', type=str, default='postgres', help='Database name')
    parser.add_argument('--username', type=str, default='admin', help='Database username')
    parser.add_argument('--table-name', type=str, default='churn_data', help='Table name to create/insert into')
    parser.add_argument('--batch-size', type=int, default=3000, help='Batch size for inserts (Aurora DSQL limit: 3000)')
    parser.add_argument('--drop-existing', action='store_true', help='Drop existing table before creating new one')
    return parser.parse_args()


def assign_tier(company_size):
    if company_size == "Enterprise":
        return np.random.choice(["Premium", "Enterprise"], p=[0.2, 0.8])
    elif company_size == "Mid-Market":
        return np.random.choice(["Standard", "Premium"], p=[0.6, 0.4])
    else:
        return np.random.choice(["Free", "Standard"], p=[0.4, 0.6])


def simulate_tenant_journey(tenant_row, snapshot_date, churn_threshold):
    tier = tenant_row["tier"]
    tenant_state = {"open_tickets": 0, "outage_count": 0, "feature_count": 0, "csm_touches": 0, "sla_misses": 0}

    if tier == "Enterprise":
        satisfaction, decay = 95.0, 0.1
    elif tier == "Premium":
        satisfaction, decay = 90.0, 0.15
    elif tier == "Standard":
        satisfaction, decay = 85.0, 0.2
    else:
        satisfaction, decay = 75.0, 0.3

    is_churning, churn_reason, churn_date = False, None, pd.NaT
    current_date = tenant_row["signup_date"]

    global_events = sorted([e for e in EVENTS if e["trigger"] == "global"], key=lambda x: x["date"])
    prob_events = [e for e in EVENTS if e["trigger"] == "prob" and e["cat"] != "External"]
    external_events = [e for e in EVENTS if e["cat"] == "External"]

    while current_date < snapshot_date and not is_churning:
        for event in external_events:
            if np.random.rand() < event["prob"]:
                is_churning, churn_reason, churn_date = True, event["type"], current_date
                break
        if is_churning:
            break

        satisfaction -= decay

        for event in global_events:
            if event["date"].year == current_date.year and event["date"].month == current_date.month:
                if event["type"] == "PriceIncrease" and tier == "Free":
                    continue
                if event["type"] == "FreeTierNerfed" and tier != "Free":
                    continue

                modifier = 2.0 if tenant_row["personality"] == event["trait"] else 1.0
                satisfaction += event["impact"] * modifier
                event["update"](tenant_state)
                if satisfaction < churn_threshold:
                    is_churning, churn_reason, churn_date = True, event["type"], current_date
                    break
        if is_churning:
            break

        for event in prob_events:
            if event["type"] == "EnterpriseSupportSLA_Miss" and tier != "Enterprise":
                continue
            if event["type"] == "ProactiveCSMOutreach" and tier not in ["Premium", "Enterprise"]:
                continue

            if np.random.rand() < event["prob"]:
                modifier = 2.0 if tenant_row["personality"] == event["trait"] else 1.0
                satisfaction += event["impact"] * modifier
                event["update"](tenant_state)
                if satisfaction < churn_threshold:
                    is_churning, churn_reason, churn_date = True, event["type"], current_date
                    break
        if is_churning:
            break

        current_date += relativedelta(months=1)
        satisfaction = max(0, min(100, satisfaction))

    return int(is_churning), churn_reason, churn_date, round(satisfaction), tenant_state


def generate_churn_data(args):
    if args.seed:
        np.random.seed(args.seed)

    snapshot_date = datetime.strptime(args.end, "%Y-%m-%d")
    start_date = datetime(2020, 1, 1)

    tenants_list = []
    for i in tqdm(range(args.num_tenants), desc="Generating tenants"):
        tenant = {
            "customerID": f"tenant_{i}",
            "signup_date": start_date + relativedelta(days=np.random.randint(0, (snapshot_date - start_date).days)),
            "contract_type": np.random.choice(["Monthly", "Annual"], p=[0.7, 0.3]),
            "company_size": np.random.choice(["Startup", "Mid-Market", "Enterprise"], p=[0.5, 0.4, 0.1]),
        }
        tenant["tier"] = assign_tier(tenant["company_size"])
        tenant["personality"] = np.random.choice(PERSONALITY_TRAITS)
        tenants_list.append(tenant)

    df = pd.DataFrame(tenants_list)

    tqdm.pandas(desc="Simulating journeys")
    results = df.progress_apply(
        lambda row: simulate_tenant_journey(row, snapshot_date, args.churn_threshold), axis=1, result_type="expand"
    )
    df[["churn", "churn_reason", "churn_date", "satisfaction", "tenant_state"]] = results

    for field in ["open_tickets", "outage_count", "feature_count", "csm_touches", "sla_misses"]:
        df[field] = df["tenant_state"].apply(lambda x: x.get(field, 0))
    df = df.drop("tenant_state", axis=1)

    final_df = df.copy()
    final_df["churn_type"] = final_df["churn_reason"].apply(
        lambda x: "involuntary" if x in ["Acquisition", "GoesOutOfBusiness"] else "voluntary" if pd.notna(x) else None
    )

    return final_df


def get_auth_token(cluster_endpoint, region):
    client = boto3.client('dsql', region_name=region)
    token = client.generate_db_connect_admin_auth_token(
        Hostname=cluster_endpoint,
        Region=region,
        ExpiresIn=3600
    )
    return token


def connect_to_aurora_dsql(cluster_endpoint, database, username, region):
    token = get_auth_token(cluster_endpoint, region)
    
    conn = psycopg2.connect(
        host=cluster_endpoint,
        port=5432,
        database=database,
        user=username,
        password=token,
        sslmode='require'
    )
    return conn


def create_churn_table(args):
    cluster_endpoint = f'{args.cluster_id}.dsql.{args.region}.on.aws'
    conn = connect_to_aurora_dsql(cluster_endpoint, args.database, args.username, args.region)
    conn.autocommit = True
    cursor = conn.cursor()
    
    if args.drop_existing:
        cursor.execute(f"DROP TABLE IF EXISTS {args.table_name}")
        print(f"Dropped existing table {args.table_name}")
    
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {args.table_name} (
        customer_id VARCHAR(50) PRIMARY KEY,
        signup_date DATE,
        company_size VARCHAR(20),
        contract_type VARCHAR(20),
        tier VARCHAR(20),
        churn BOOLEAN,
        churn_reason VARCHAR(50),
        churn_date DATE,
        churn_type VARCHAR(20),
        open_tickets INTEGER,
        outage_count INTEGER,
        feature_count INTEGER,
        csm_touches INTEGER,
        sla_misses INTEGER
    )
    """

    cursor.execute(create_table_sql)
    cursor.close()
    conn.close()


def insert_churn_data(df, args):
    cluster_endpoint = f'{args.cluster_id}.dsql.{args.region}.on.aws'
    conn = connect_to_aurora_dsql(cluster_endpoint, args.database, args.username, args.region)
    cursor = conn.cursor()
    
    data_tuples = []
    for _, row in df.iterrows():
        tuple_data = (
            row['customerID'],
            datetime.strptime(row['signup_date'], '%Y-%m-%d').date() if pd.notna(row['signup_date']) else None,
            row['company_size'],
            row['contract_type'],
            row['tier'],
            bool(row['churn']),
            row['churn_reason'] if pd.notna(row['churn_reason']) else None,
            datetime.strptime(row['churn_date'], '%Y-%m-%d').date() if pd.notna(row['churn_date']) and row['churn_date'] != 'NaT' else None,
            row['churn_type'] if pd.notna(row['churn_type']) else None,
            int(row['open_tickets']),
            int(row['outage_count']),
            int(row['feature_count']),
            int(row['csm_touches']),
            int(row['sla_misses'])
        )
        data_tuples.append(tuple_data)
    
    insert_sql = f"""
    INSERT INTO {args.table_name} VALUES %s
    ON CONFLICT (customer_id) DO UPDATE SET
        signup_date = EXCLUDED.signup_date,
        company_size = EXCLUDED.company_size,
        contract_type = EXCLUDED.contract_type,
        tier = EXCLUDED.tier,
        churn = EXCLUDED.churn,
        churn_reason = EXCLUDED.churn_reason,
        churn_date = EXCLUDED.churn_date,
        churn_type = EXCLUDED.churn_type,
        open_tickets = EXCLUDED.open_tickets,
        outage_count = EXCLUDED.outage_count,
        feature_count = EXCLUDED.feature_count,
        csm_touches = EXCLUDED.csm_touches,
        sla_misses = EXCLUDED.sla_misses
    """
    
    total_inserted = 0
    batches = range(0, len(data_tuples), args.batch_size)
    for i in tqdm(batches, desc="Inserting batches"):
        batch = data_tuples[i:i + args.batch_size]
        execute_values(cursor, insert_sql, batch)
        conn.commit()
        total_inserted += len(batch)
    
    cursor.close()
    conn.close()
    
    print(f"Successfully inserted {total_inserted} records into Aurora DSQL table {args.table_name}!")


def main():
    args = parse_args()
    
    print(f"Generating {args.num_tenants} tenant records...")
    df = generate_churn_data(args)
    
    df["signup_date"] = df["signup_date"].dt.strftime("%Y-%m-%d")
    df["churn_date"] = df["churn_date"].apply(lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else None)
    
    print("Creating table...")
    create_churn_table(args)
    
    print("Inserting data...")
    insert_churn_data(df, args)
    
    print("Data successfully loaded to Aurora DSQL!")


if __name__ == "__main__":
    main()

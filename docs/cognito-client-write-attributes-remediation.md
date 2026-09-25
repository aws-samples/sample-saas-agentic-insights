# Remediate Cognito app client write attributes

Use this guide to restrict tenant-facing Amazon Cognito app clients and migrate
existing deployments. It contains operational remediation steps only and omits
sensitive ticket and abuse details.

New deployments, statically defined Basic and Premium clients, and newly
provisioned Premium clients allow users to write only their own standard `email`
attribute. Deploying the updated code does not change app clients that already
exist.

## Prerequisites

- Use Python 3 with `boto3` installed.
- Configure AWS credentials for the account that owns the target user pools.
- Allow the operator to call `cognito-idp:DescribeUserPoolClient` and
  `cognito-idp:UpdateUserPoolClient` on each target.
- Obtain the user pool ID and app client ID for every existing tenant-facing
  client in the deployment.
- Store the target file outside source control if its identifiers are sensitive
  in your environment.

## Prepare the target file

1. Create a JSON file with a non-empty `targets` array.

   Each target must contain one `user_pool_id` and one `client_id`. Do not add
   credentials, client secrets, user details, or ticket content.

   ```json
   {
     "targets": [
       {
         "user_pool_id": "ap-southeast-2_example",
         "client_id": "client-example-123"
       },
       {
         "user_pool_id": "ap-southeast-2_another",
         "client_id": "client-another-456"
       }
     ]
   }
   ```

2. Confirm that each pool and client pair belongs to the intended deployment.

   The migration changes only the clients listed in this file. It rejects empty,
   duplicate, missing, or malformed identifiers.

## Run the migration

1. From the repository root, run the migration without `--apply`.

   ```bash
   python3 scripts/migrations/restrict_cognito_client_write_attributes.py \
     --input migration-targets.json \
     --region ap-southeast-2
   ```

   Dry-run is the default. Confirm that the output says `Mode: dry-run`, reports
   the expected target count, and lists only the intended pool and client pairs
   as `would update`.

2. Resolve every dry-run error before continuing.

   Do not apply a partial or unreviewed target list.

3. Run the same command with `--apply`.

   ```bash
   python3 scripts/migrations/restrict_cognito_client_write_attributes.py \
     --input migration-targets.json \
     --region ap-southeast-2 \
     --apply
   ```

   The script preserves supported client settings and replaces
   `WriteAttributes` with `["email"]`. It stops on the first AWS API error, so a
   failed run may have updated earlier targets. Check every target before
   retrying.

4. Verify each migrated client.

   ```bash
   aws cognito-idp describe-user-pool-client \
     --user-pool-id "$USER_POOL_ID" \
     --client-id "$CLIENT_ID" \
     --region "$AWS_REGION" \
     --query 'UserPoolClient.WriteAttributes'
   ```

   The command must return only `email`.

## Reconcile users and contain existing sessions

The client restriction prevents future self-writes. It does not prove that
existing `custom:role` or `custom:tier` values are correct, and it does not
invalidate sessions issued before migration.

1. Compare every affected user's `custom:role` and `custom:tier` with the
   authoritative tenant and administrator records.

2. Correct each mismatch through an administrator-authorized path.

   For AWS CLI administration, set the expected values from the authoritative
   records:

   ```bash
   aws cognito-idp admin-update-user-attributes \
     --user-pool-id "$USER_POOL_ID" \
     --username "$USERNAME" \
     --region "$AWS_REGION" \
     --user-attributes \
       Name=custom:role,Value="$EXPECTED_ROLE" \
       Name=custom:tier,Value="$EXPECTED_TIER"
   ```

3. After reconciliation, revoke each affected user's Cognito sessions.

   ```bash
   aws cognito-idp admin-user-global-sign-out \
     --user-pool-id "$USER_POOL_ID" \
     --username "$USERNAME" \
     --region "$AWS_REGION"
   ```

   This revokes refresh tokens, but the sample's Lambda authorizer validates JWTs
   locally and does not query Cognito revocation state. Already issued access or
   ID tokens can therefore remain valid until their `exp` time.

4. Quarantine affected identities from application APIs until every token issued
   before reconciliation has expired.

   Use an application-level denylist keyed by a trusted user identifier. If the
   deployment has no denylist, suspend the affected tenant's API access. Determine
   the quarantine period from each app client's configured access and ID token
   validity; dedicated Premium clients in this sample use an eight-hour lifetime.
   Do not rely on global sign-out alone.

5. After the quarantine period, require users to authenticate again and confirm
   that their new tokens contain the reconciled role and tier before restoring
   access.

Do not use current token claims or user-supplied values as the reconciliation
source. Keep an administrative record of the clients checked, users reconciled,
and sessions revoked without recording tokens or secrets.

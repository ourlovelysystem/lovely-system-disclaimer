#!/usr/bin/env bash
set -euo pipefail

TABLE_NAME="lovely-system-disclaimer"
FUNCTION_NAME="lovely-system-disclaimer"
ROLE_NAME="lovely-system-disclaimer-lambda"
API_NAME="lovely-system-disclaimer"

REGION="$(aws configure get region 2>/dev/null || true)"
if [[ -z "${REGION}" ]]; then
  REGION="us-east-1"
fi

ACCOUNT_ID="$(
  aws sts get-caller-identity \
    --query Account \
    --output text
)"

echo "Account: ${ACCOUNT_ID}"
echo "Region:  ${REGION}"
echo

if aws dynamodb describe-table \
  --table-name "${TABLE_NAME}" \
  --region "${REGION}" \
  >/dev/null 2>&1
then
  echo "DynamoDB already exists: ${TABLE_NAME}"
else
  echo "Creating DynamoDB table..."

  aws dynamodb create-table \
    --table-name "${TABLE_NAME}" \
    --region "${REGION}" \
    --attribute-definitions \
      AttributeName=pk,AttributeType=S \
      AttributeName=sk,AttributeType=S \
    --key-schema \
      AttributeName=pk,KeyType=HASH \
      AttributeName=sk,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    >/dev/null

  aws dynamodb wait table-exists \
    --table-name "${TABLE_NAME}" \
    --region "${REGION}"
fi

TABLE_ARN="$(
  aws dynamodb describe-table \
    --table-name "${TABLE_NAME}" \
    --region "${REGION}" \
    --query 'Table.TableArn' \
    --output text
)"

echo "DynamoDB: ${TABLE_NAME}"

cat > /tmp/lovely-disclaimer-trust.json <<'JSON'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
JSON

if aws iam get-role \
  --role-name "${ROLE_NAME}" \
  >/dev/null 2>&1
then
  echo "IAM role already exists: ${ROLE_NAME}"
else
  echo "Creating Lambda execution role..."

  aws iam create-role \
    --role-name "${ROLE_NAME}" \
    --assume-role-policy-document \
      file:///tmp/lovely-disclaimer-trust.json \
    >/dev/null
fi

aws iam attach-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-arn \
    arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

cat > /tmp/lovely-disclaimer-dynamodb.json <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:Query"
      ],
      "Resource": "${TABLE_ARN}"
    }
  ]
}
JSON

aws iam put-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-name lovely-system-disclaimer-dynamodb \
  --policy-document \
    file:///tmp/lovely-disclaimer-dynamodb.json

ROLE_ARN="$(
  aws iam get-role \
    --role-name "${ROLE_NAME}" \
    --query 'Role.Arn' \
    --output text
)"

echo "IAM role: ${ROLE_NAME}"

SCRIPT_DIR="$(
  cd "$(dirname "${BASH_SOURCE[0]}")" \
  && pwd
)"

rm -f "${SCRIPT_DIR}/function.zip"

(
  cd "${SCRIPT_DIR}"
  zip -q function.zip lambda_function.py
)

if aws lambda get-function \
  --function-name "${FUNCTION_NAME}" \
  --region "${REGION}" \
  >/dev/null 2>&1
then
  echo "Updating Lambda function..."

  aws lambda update-function-code \
    --function-name "${FUNCTION_NAME}" \
    --region "${REGION}" \
    --zip-file \
      "fileb://${SCRIPT_DIR}/function.zip" \
    >/dev/null

  aws lambda wait function-updated-v2 \
    --function-name "${FUNCTION_NAME}" \
    --region "${REGION}"

  aws lambda update-function-configuration \
    --function-name "${FUNCTION_NAME}" \
    --region "${REGION}" \
    --runtime python3.13 \
    --handler lambda_function.lambda_handler \
    --timeout 10 \
    --memory-size 128 \
    --environment \
      "Variables={TABLE_NAME=${TABLE_NAME}}" \
    >/dev/null

  aws lambda wait function-updated-v2 \
    --function-name "${FUNCTION_NAME}" \
    --region "${REGION}"

else
  echo "Creating Lambda function..."

  CREATED="false"

  for ATTEMPT in {1..12}; do
    if aws lambda create-function \
      --function-name "${FUNCTION_NAME}" \
      --region "${REGION}" \
      --runtime python3.13 \
      --role "${ROLE_ARN}" \
      --handler lambda_function.lambda_handler \
      --zip-file \
        "fileb://${SCRIPT_DIR}/function.zip" \
      --timeout 10 \
      --memory-size 128 \
      --environment \
        "Variables={TABLE_NAME=${TABLE_NAME}}" \
      >/dev/null 2>&1
    then
      CREATED="true"
      break
    fi

    echo "Waiting for IAM propagation (${ATTEMPT}/12)..."
    sleep 5
  done

  if [[ "${CREATED}" != "true" ]]; then
    echo "Unable to create Lambda function."
    exit 1
  fi
fi

aws lambda wait function-active-v2 \
  --function-name "${FUNCTION_NAME}" \
  --region "${REGION}"

FUNCTION_ARN="$(
  aws lambda get-function \
    --function-name "${FUNCTION_NAME}" \
    --region "${REGION}" \
    --query 'Configuration.FunctionArn' \
    --output text
)"

echo "Lambda: ${FUNCTION_NAME}"

API_ID="$(
  aws apigatewayv2 get-apis \
    --region "${REGION}" \
    --query \
      "Items[?Name=='${API_NAME}'].ApiId | [0]" \
    --output text
)"

if [[ -z "${API_ID}" || "${API_ID}" == "None" ]]; then
  echo "Creating HTTP API..."

  API_JSON="$(
    aws apigatewayv2 create-api \
      --region "${REGION}" \
      --name "${API_NAME}" \
      --protocol-type HTTP \
      --target "${FUNCTION_ARN}" \
      --cors-configuration \
        'AllowOrigins=["*"],AllowMethods=["GET","POST","OPTIONS"],AllowHeaders=["Content-Type"],MaxAge=86400'
  )"

  API_ID="$(
    printf '%s' "${API_JSON}" \
      | python3 -c \
        'import json,sys; print(json.load(sys.stdin)["ApiId"])'
  )"
else
  echo "HTTP API already exists: ${API_ID}"
fi

API_ENDPOINT="$(
  aws apigatewayv2 get-api \
    --region "${REGION}" \
    --api-id "${API_ID}" \
    --query 'ApiEndpoint' \
    --output text
)"

STATEMENT_ID="allow-apigateway-${API_ID}"

POLICY="$(
  aws lambda get-policy \
    --function-name "${FUNCTION_NAME}" \
    --region "${REGION}" \
    --query Policy \
    --output text \
    2>/dev/null \
    || true
)"

if printf '%s' "${POLICY}" \
  | grep -q "${STATEMENT_ID}"
then
  echo "API Gateway invoke permission already exists."
else
  aws lambda add-permission \
    --function-name "${FUNCTION_NAME}" \
    --region "${REGION}" \
    --statement-id "${STATEMENT_ID}" \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn \
      "arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/*" \
    >/dev/null

  echo "Added API Gateway invoke permission."
fi

cat > "${SCRIPT_DIR}/backend.json" <<JSON
{
  "account": "${ACCOUNT_ID}",
  "region": "${REGION}",
  "table": "${TABLE_NAME}",
  "function": "${FUNCTION_NAME}",
  "api_id": "${API_ID}",
  "api_endpoint": "${API_ENDPOINT}"
}
JSON

echo
echo "Backend deployed."
echo "API endpoint: ${API_ENDPOINT}"
echo

echo "Testing GET /health..."
curl -fsS "${API_ENDPOINT}/health"
echo
echo

echo "Creating deployment-test participant..."

PARTICIPANT_JSON="$(
  curl -fsS \
    -X POST \
    "${API_ENDPOINT}/participants" \
    -H 'Content-Type: application/json' \
    -d '{"declared_name":"Deployment Test"}'
)"

PARTICIPANT_ID="$(
  printf '%s' "${PARTICIPANT_JSON}" \
    | python3 -c \
      'import json,sys; print(json.load(sys.stdin)["participant_id"])'
)"

echo "Participant: ${PARTICIPANT_ID}"
echo

echo "Requesting first question..."

QUESTION_JSON="$(
  curl -fsS \
    "${API_ENDPOINT}/participants/${PARTICIPANT_ID}/next"
)"

printf '%s\n' "${QUESTION_JSON}"

QUESTION_ID="$(
  printf '%s' "${QUESTION_JSON}" \
    | python3 -c \
      'import json,sys; print(json.load(sys.stdin)["question"]["question_id"])'
)"

echo
echo "Answering first question YES..."

ANSWER_JSON="$(
  curl -fsS \
    -X POST \
    "${API_ENDPOINT}/participants/${PARTICIPANT_ID}/answer" \
    -H 'Content-Type: application/json' \
    -d "{\"question_id\":\"${QUESTION_ID}\",\"response\":\"yes\"}"
)"

printf '%s\n' "${ANSWER_JSON}"

echo
echo "Retrieving participant record..."

curl -fsS \
  "${API_ENDPOINT}/participants/${PARTICIPANT_ID}"

echo
echo
echo "Deployment complete."

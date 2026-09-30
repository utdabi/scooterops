import boto3

session = boto3.Session(
    profile_name="scooterops",
    region_name="us-east-1"
)

client = session.client("bedrock-runtime")

response = client.converse(
    modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "text": (
                        "Reply with exactly: "
                        "ScooterOps Bedrock connection successful."
                    )
                }
            ]
        }
    ],
    inferenceConfig={
        "maxTokens": 30,
        "temperature": 0
    }
)

print(
    response["output"]["message"]["content"][0]["text"]
)
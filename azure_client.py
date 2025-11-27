# azure_client.py
import os
from openai import AzureOpenAI

def get_azure_client(profile: str = "4O") -> AzureOpenAI:
    key = os.getenv(f"AZURE_API_KEY_{profile.upper()}")
    endpoint = os.getenv(f"AZURE_ENDPOINT_{profile.upper()}")
    version = os.getenv(f"AZURE_API_VERSION_{profile.upper()}", "2024-06-01")
    if not key or not endpoint:
        raise RuntimeError(f"Azure env not set for profile={profile}")

    return AzureOpenAI(
        api_key=key,
        azure_endpoint=endpoint,
        api_version=version,
    )

def get_azure_deployment(profile: str = "4O") -> str:
    dep = os.getenv(f"AZURE_DEPLOYMENT_{profile.upper()}")
    if not dep:
        raise RuntimeError(f"Azure deployment not set for profile={profile}")
    return dep

from mcp.server.fastmcp import FastMCP
import os
import requests
import json


mcp = FastMCP(name="InfluxDB v1.x")


@mcp.tool()
def query_influxdb(influxql_query: str) -> str:
    """
    InfluxDB 시계열 데이터베이스에 InfluxQL 쿼리를 실행하여 시스템 메트릭(CPU, 메모리 등)을 분석할 때 사용합니다.
    """
    INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
    INFLUXDB_USER = os.getenv("INFLUXDB_USER", "mc-agent")
    INFLUXDB_PASSWORD = os.getenv("INFLUXDB_PASSWORD", "mc-agent")
    DEFAULT_DB = "mc-observability"

    try:
        params = {
            "u": INFLUXDB_USER,
            "p": INFLUXDB_PASSWORD,
            "db": DEFAULT_DB,
            "q": influxql_query,
        }
        response = requests.get(f"{INFLUXDB_URL}/query", params=params)
        response.raise_for_status()

        return response.text

    except requests.exceptions.HTTPError as http_err:
        return json.dumps(
            {
                "error": f"HTTP Error: {http_err.response.status_code}",
                "response_body": http_err.response.text,
            }
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run(transport="stdio")

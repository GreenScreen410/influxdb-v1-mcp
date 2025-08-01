# influxdb_mcp_full_tools.py
from mcp.server.fastmcp import FastMCP
import os
import requests
import json

from src.config import DB_NAME, MCP_READ_ONLY, logger
from typing import List, Any, Dict


# --- 1. MCP 인스턴스 생성 ---
mcp = FastMCP(
    title="InfluxDB Full Toolkit MCP",
    description="InfluxDB 데이터베이스의 구조를 탐색하고, 데이터를 쿼리하며, 데이터베이스를 관리하는 완벽한 도구 세트를 제공합니다.",
    version="2.0.0",
)


# --- 2. InfluxDB 연결을 위한 헬퍼 함수 ---
def _execute_influx_query(query: str, database: str = None, method: str = "GET") -> str:
    """InfluxDB에 쿼리를 실행하고 결과를 텍스트로 반환하는 내부 헬퍼 함수"""
    INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
    INFLUXDB_USER = os.getenv("INFLUXDB_USER", "")
    INFLUXDB_PASSWORD = os.getenv("INFLUXDB_PASSWORD", "")

    try:
        params = {"u": INFLUXDB_USER, "p": INFLUXDB_PASSWORD}
        if database:
            params["db"] = database

        # 쓰기 작업은 POST, 읽기 작업은 GET을 사용
        if method.upper() == "POST":
            params["q"] = query
            response = requests.post(f"{INFLUXDB_URL}/query", params=params)
        else:  # GET
            params["q"] = query
            response = requests.get(f"{INFLUXDB_URL}/query", params=params)

        response.raise_for_status()
        return response.text

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP Error: {http_err.response.status_code}, Response: {http_err.response.text}")
        return json.dumps(
            {
                "error": f"HTTP Error: {http_err.response.status_code}",
                "response_body": http_err.response.text,
            }
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return json.dumps({"error": str(e)})


def _parse_influx_response(response_text: str) -> List[Dict[str, Any]]:
    """InfluxDB JSON 응답을 파싱하여 결과 리스트로 변환"""
    try:
        data = json.loads(response_text)
        if "results" not in data or not data["results"]:
            return []

        results = []
        for result in data["results"]:
            if "series" in result and result["series"]:
                for series in result["series"]:
                    columns = series.get("columns", [])
                    values = series.get("values", [])
                    for value_set in values:
                        results.append(dict(zip(columns, value_set)))
        return results
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.error(f"Failed to parse InfluxDB response: {e}\nResponse text: {response_text[:500]}")
        return [{"error": "Failed to parse response", "raw_response": response_text}]


# --- 3. 모든 도구 구현 ---


@mcp.tool()
def list_databases() -> List[str]:
    """[관리] 접근 가능한 모든 InfluxDB 데이터베이스의 목록을 반환합니다."""
    logger.info("TOOL START: list_databases")
    response_text = _execute_influx_query("SHOW DATABASES")
    parsed = _parse_influx_response(response_text)
    # InfluxDB 1.x에서 SHOW DATABASES는 'name' 필드를 포함하는 리스트를 반환합니다.
    db_list = [row.get("name") for row in parsed if "name" in row]
    logger.info(f"TOOL END: list_databases completed. Found {len(db_list)} databases.")
    return db_list


@mcp.tool()
def list_measurements(database_name: str) -> List[str]:
    """[구조 탐색] 지정된 데이터베이스의 모든 측정값(Measurement, 테이블과 유사) 목록을 반환합니다."""
    logger.info(f"TOOL START: list_measurements for database '{database_name}'")
    response_text = _execute_influx_query("SHOW MEASUREMENTS", database=database_name)
    parsed = _parse_influx_response(response_text)
    # SHOW MEASUREMENTS는 'name' 필드를 포함하는 리스트를 반환합니다.
    measurement_list = [row.get("name") for row in parsed if "name" in row]
    logger.info(f"TOOL END: list_measurements completed. Found {len(measurement_list)} measurements.")
    return measurement_list


@mcp.tool()
def get_measurement_schema(measurement_name: str, database_name: str) -> str:
    """[구조 탐색] 특정 측정값의 스키마, 즉 모든 필드(field)와 태그(tag)의 목록과 타입을 반환합니다. 쿼리 생성 전 필수 확인 도구입니다."""
    logger.info(f"TOOL START: get_measurement_schema for '{database_name}'.'{measurement_name}'")
    fields_query = f'SHOW FIELD KEYS FROM "{measurement_name}"'
    tags_query = f'SHOW TAG KEYS FROM "{measurement_name}"'

    fields_result_text = _execute_influx_query(fields_query, database=database_name)
    tags_result_text = _execute_influx_query(tags_query, database=database_name)

    try:
        fields_data = json.loads(fields_result_text)
        tags_data = json.loads(tags_result_text)

        # LLM이 이해하기 쉽게 결과를 재구성
        schema = {
            "measurement": measurement_name,
            "database": database_name,
            "fields": [item[0] for item in fields_data.get("results", [{}])[0].get("series", [{}])[0].get("values", [])],
            "tags": [item[0] for item in tags_data.get("results", [{}])[0].get("series", [{}])[0].get("values", [])],
        }
        logger.info(f"TOOL END: get_measurement_schema completed successfully for '{database_name}'.'{measurement_name}'.")
        return json.dumps(schema, indent=2)
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        logger.error(f"Error parsing schema for '{database_name}'.'{measurement_name}': {e}")
        return json.dumps(
            {
                "error": "Failed to parse schema",
                "details": str(e),
                "raw_fields_response": fields_result_text,
                "raw_tags_response": tags_result_text,
            }
        )


@mcp.tool()
def execute_influxql(influxql_query: str, database_name: str = DB_NAME) -> str:
    """[데이터 실행] 읽기 전용 InfluxQL 쿼리(SELECT, SHOW)를 실행하여 실제 데이터를 가져옵니다."""
    logger.info(f"TOOL START: execute_influxql on database '{database_name}'")
    safe_query = influxql_query.strip().upper()

    is_read_query = safe_query.startswith("SELECT") or safe_query.startswith("SHOW")

    if MCP_READ_ONLY and not is_read_query:
        logger.warning(f"Blocked non-read-only query in read-only mode: {influxql_query[:100]}")
        return json.dumps({"error": "SecurityError: Only SELECT and SHOW queries are allowed in read-only mode."})

    if not is_read_query:
        logger.warning(f"Executing a non-standard read query: {influxql_query[:100]}")

    result = _execute_influx_query(influxql_query, database=database_name)
    logger.info("TOOL END: execute_influxql completed.")
    return result


@mcp.tool()
def create_database(database_name: str) -> str:
    """[관리] 새로운 데이터베이스를 생성합니다. 이미 존재하면 아무 작업도 하지 않습니다."""
    logger.info(f"TOOL START: create_database '{database_name}'")
    if MCP_READ_ONLY:
        logger.warning("Blocked CREATE DATABASE in read-only mode.")
        return json.dumps({"error": "SecurityError: Cannot create database in read-only mode."})

    query = f'CREATE DATABASE "{database_name}"'
    result = _execute_influx_query(query, method="POST")
    logger.info("TOOL END: create_database completed.")
    return result


if __name__ == "__main__":
    # 로깅 및 환경 변수가 올바르게 설정되었는지 확인
    logger.info("MCP Server starting...")
    logger.info(f"Default database: {DB_NAME}")

    # 서버 실행
    mcp.run(transport="stdio")

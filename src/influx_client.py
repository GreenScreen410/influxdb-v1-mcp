# influx_client.py
import requests
import json
import os


class InfluxDBClient:
    """
    A client class for managing all HTTP communications with InfluxDB v1.x.
    This class encapsulates connection details and provides clear methods for interacting with the database.
    It uses environment variables for configuration, with fallback defaults.

    Attributes:
        base_url (str): The base URL of the InfluxDB instance (default: "http://localhost:8086").
        user (str): The username for authentication (default: "mc-agent").
        password (str): The password for authentication (default: "mc-agent").
    """

    def __init__(self):
        """
        Initializes the InfluxDBClient with connection details from environment variables.
        If environment variables are not set, fallback defaults are used.

        Environment Variables:
            INFLUXDB_URL: The URL of the InfluxDB server.
            INFLUXDB_USER: The username for authentication.
            INFLUXDB_PASSWORD: The password for authentication.
        """
        self.base_url = os.getenv("INFLUXDB_URL", "http://localhost:8086")
        self.user = os.getenv("INFLUXDB_USER", "mc-agent")
        self.password = os.getenv("INFLUXDB_PASSWORD", "mc-agent")

    def execute_query(self, query: str, database: str = None) -> str:
        """
        Executes a query on InfluxDB and returns the result as a JSON formatted string.

        This method sends a GET request to the InfluxDB query endpoint with the provided query.
        Authentication is handled using the configured username and password.

        Args:
            query (str): The InfluxQL query to execute.
            database (str, optional): The name of the database to query. If not provided, the query
                                      must specify the database internally or use the default.

        Returns:
            str: A JSON-formatted string containing the query result or an error message.

        Raises:
            requests.exceptions.HTTPError: If the HTTP request fails (handled internally and returned as JSON).
            Exception: For other unexpected errors (handled internally and returned as JSON).
        """
        try:
            params = {
                "u": self.user,
                "p": self.password,
                "q": query,
            }
            if database:
                params["db"] = database

            response = requests.get(f"{self.base_url}/query", params=params, headers={"Accept": "application/json"})
            response.raise_for_status()

            # InfluxDB로부터 받은 응답을 JSON으로 파싱
            # 성공적인 응답을 나타내는 JSON 구조 생성
            return json.dumps({"status": "success", "data": response.json()})

        except requests.exceptions.HTTPError as http_err:
            return json.dumps(
                {
                    "status": "error",
                    "error": "HTTP Error",
                    "message": f"Status Code: {http_err.response.status_code}",
                    "response_body": http_err.response.text,
                }
            )
        except Exception as e:
            return json.dumps({"status": "error", "error": "Exception", "message": str(e)})

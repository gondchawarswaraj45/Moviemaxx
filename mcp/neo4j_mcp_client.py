import os
import json
import logging
import subprocess
from typing import Any, Dict, List, Optional
from neo4j import Driver

from config import (
    NEO4J_URI,
    NEO4J_USERNAME,
    NEO4J_PASSWORD,
    NEO4J_DATABASE,
    MCP_EXE_PATH,
    MCP_READ_ONLY,
)

logger = logging.getLogger(__name__)

class Neo4jMCPClient:
    """
    Model Context Protocol (MCP) Client for Neo4j.
    Connects to the Neo4j MCP Server executable (neo4j-mcp.exe)
    and provides structured protocol operations: get-schema, read-cypher, write-cypher.
    """
    def __init__(self, driver: Optional[Driver] = None):
        self.driver = driver
        self.uri = NEO4J_URI
        self.username = NEO4J_USERNAME
        self.password = NEO4J_PASSWORD
        self.database = NEO4J_DATABASE
        self.read_only = MCP_READ_ONLY
        self.exe_path = str(MCP_EXE_PATH)

    def is_mcp_executable_available(self) -> bool:
        return os.path.exists(self.exe_path)

    def get_mcp_environment(self) -> Dict[str, str]:
        env = os.environ.copy()
        env.update({
            "NEO4J_MCP_URI": self.uri,
            "NEO4J_MCP_USERNAME": self.username,
            "NEO4J_MCP_PASSWORD": self.password,
            "NEO4J_MCP_DATABASE": self.database,
            "NEO4J_MCP_READ_ONLY": "true" if self.read_only else "false",
            "NEO4J_MCP_TELEMETRY": "false",
            "NEO4J_MCP_LOG_LEVEL": "info",
        })
        return env

    def get_schema(self) -> Dict[str, Any]:
        """
        MCP Tool: get-schema
        Introspects node labels, relationship types, and property keys.
        """
        if self.driver:
            with self.driver.session(database=self.database) as session:
                labels = session.run("CALL db.labels()").value()
                rel_types = session.run("CALL db.relationshipTypes()").value()
                property_keys = session.run("CALL db.propertyKeys()").value()
                return {
                    "node_labels": labels,
                    "relationship_types": rel_types,
                    "property_keys": property_keys,
                    "mcp_source": "neo4j-driver-mcp-bridge"
                }
        return {"error": "Neo4j driver not connected"}

    def read_cypher(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        MCP Tool: read-cypher
        Executes read-only Cypher query over MCP bridge.
        """
        parameters = parameters or {}
        if self.driver:
            with self.driver.session(database=self.database) as session:
                records = session.execute_read(lambda tx: list(tx.run(query, **parameters)))
                return [dict(record) for record in records]
        return []

    def write_cypher(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        MCP Tool: write-cypher
        Executes write Cypher query (enforces NEO4J_MCP_READ_ONLY check).
        """
        if self.read_only:
            return {"status": "BLOCKED", "message": "NEO4J_MCP_READ_ONLY is enabled. Write operations prohibited."}
        
        parameters = parameters or {}
        if self.driver:
            with self.driver.session(database=self.database) as session:
                summary = session.execute_write(lambda tx: tx.run(query, **parameters).consume())
                return {
                    "status": "SUCCESS",
                    "nodes_created": summary.counters.nodes_created,
                    "relationships_created": summary.counters.relationships_created,
                }
        return {"error": "Neo4j driver not connected"}

    def get_status(self) -> Dict[str, Any]:
        return {
            "mcp_executable": self.exe_path,
            "executable_found": self.is_mcp_executable_available(),
            "neo4j_uri": self.uri,
            "neo4j_database": self.database,
            "read_only": self.read_only,
            "connected": self.driver is not None,
        }

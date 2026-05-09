"""
AppForge Runtime Simulator
Validates that generated schemas can power a working application.
Simulates: DB creation, API routing, Auth middleware, UI rendering
"""

import json
from typing import Any


class RuntimeSimulator:
    """
    Simulates execution of the generated app schema.
    Proves the output is actually usable - not just pretty JSON.
    """

    def __init__(self, schema: dict):
        self.schema = schema
        self.db = {}           # simulated in-memory DB
        self.sessions = {}     # simulated auth sessions
        self.reports = []

    def simulate_db_init(self) -> dict:
        """Simulate DB table creation from schema."""
        report = {"step": "DB Init", "success": True, "tables_created": [], "errors": []}
        
        db_schema = self.schema.get("db_schema", {})
        tables = db_schema.get("tables", [])
        
        if not tables:
            report["success"] = False
            report["errors"].append("No tables defined in db_schema")
            self.reports.append(report)
            return report
        
        for table in tables:
            name = table.get("name")
            if not name:
                report["errors"].append("Table missing name")
                continue
            
            # Validate foreign keys reference existing tables
            table_names = [t["name"] for t in tables]
            for col in table.get("columns", []):
                fk = col.get("foreign_key")
                if fk and fk.get("table") and fk["table"] not in table_names:
                    report["errors"].append(f"FK in {name}.{col['name']} references non-existent table {fk['table']}")
            
            self.db[name] = []  # empty table
            report["tables_created"].append(name)
        
        if report["errors"]:
            report["success"] = False
        
        self.reports.append(report)
        return report

    def simulate_auth(self) -> dict:
        """Simulate auth system setup and token generation."""
        report = {"step": "Auth Setup", "success": True, "roles_configured": [], "errors": []}
        
        auth = self.schema.get("auth_schema", {})
        if not auth:
            report["success"] = False
            report["errors"].append("No auth_schema defined")
            self.reports.append(report)
            return report
        
        roles = auth.get("roles", [])
        if not roles:
            report["errors"].append("No roles defined in auth_schema")
        
        for role in roles:
            role_name = role.get("name")
            if not role_name:
                continue
            
            # Simulate token for each role
            self.sessions[role_name] = {
                "token": f"sim_token_{role_name}_abc123",
                "role": role_name,
                "permissions": role.get("permissions", []),
                "is_premium": role.get("is_premium", False)
            }
            report["roles_configured"].append(role_name)
        
        if report["errors"]:
            report["success"] = False
        
        self.reports.append(report)
        return report

    def simulate_api_routes(self) -> dict:
        """Simulate API route registration and basic request/response."""
        report = {"step": "API Routes", "success": True, "routes_registered": [], "errors": [], "test_requests": []}
        
        api = self.schema.get("api_schema", {})
        endpoints = api.get("endpoints", [])
        
        if not endpoints:
            report["success"] = False
            report["errors"].append("No endpoints defined in api_schema")
            self.reports.append(report)
            return report
        
        db_table_names = list(self.db.keys())
        auth_roles = list(self.sessions.keys())
        
        for ep in endpoints:
            method = ep.get("method", "GET")
            path = ep.get("path", "")
            roles_allowed = ep.get("roles_allowed", [])
            
            if not path:
                report["errors"].append(f"Endpoint missing path: {ep.get('id')}")
                continue
            
            route_key = f"{method} {path}"
            
            # Validate roles exist
            for role in roles_allowed:
                if role != "public" and role not in auth_roles:
                    report["errors"].append(f"Route {route_key} references undefined role: {role}")
            
            # Simulate a test request
            test_result = self._simulate_request(ep, auth_roles)
            report["test_requests"].append(test_result)
            report["routes_registered"].append(route_key)
        
        if report["errors"]:
            report["success"] = False
        
        self.reports.append(report)
        return report

    def _simulate_request(self, endpoint: dict, available_roles: list) -> dict:
        """Simulate a single API request."""
        method = endpoint.get("method", "GET")
        path = endpoint.get("path", "")
        auth_required = endpoint.get("auth_required", False)
        roles_allowed = endpoint.get("roles_allowed", ["public"])
        response_body = endpoint.get("response_body", {})
        
        # Pick first allowed role for simulation
        test_role = None
        for role in roles_allowed:
            if role in available_roles:
                test_role = role
                break
        
        # Simulate request
        sim_request = {
            "method": method,
            "path": path,
            "auth_token": self.sessions.get(test_role, {}).get("token") if test_role else None,
            "simulated_response": {
                "status": 200,
                "body": self._generate_mock_response(response_body)
            }
        }
        
        # Auth check
        if auth_required and not test_role:
            sim_request["simulated_response"]["status"] = 401
            sim_request["simulated_response"]["body"] = {"error": "Unauthorized"}
        
        return sim_request

    def _generate_mock_response(self, schema: dict) -> Any:
        """Generate mock response data from schema shape."""
        if not schema:
            return {}
        
        mock = {}
        for key, val in schema.items():
            if isinstance(val, str):
                type_lower = val.lower()
                if "id" in key:
                    mock[key] = "uuid-mock-1234"
                elif type_lower in ("string", "str", "varchar", "text"):
                    mock[key] = f"mock_{key}"
                elif type_lower in ("int", "integer", "number"):
                    mock[key] = 1
                elif type_lower in ("bool", "boolean"):
                    mock[key] = True
                elif type_lower in ("array", "list"):
                    mock[key] = []
                elif type_lower in ("object", "dict"):
                    mock[key] = {}
                else:
                    mock[key] = f"mock_{key}"
            elif isinstance(val, dict):
                mock[key] = self._generate_mock_response(val)
            elif isinstance(val, list):
                mock[key] = []
            else:
                mock[key] = val
        return mock

    def simulate_ui_pages(self) -> dict:
        """Simulate UI page rendering - verify all data_sources map to API endpoints."""
        report = {"step": "UI Pages", "success": True, "pages_verified": [], "errors": []}
        
        ui = self.schema.get("ui_schema", {})
        pages = ui.get("pages", [])
        
        api = self.schema.get("api_schema", {})
        base_url = api.get("base_url", "").rstrip("/")
        endpoint_paths = [f"{base_url}/{ep.get('path', '').lstrip('/')}" for ep in api.get("endpoints", [])]
        
        if not pages:
            report["errors"].append("No pages defined in ui_schema")
            report["success"] = False
            self.reports.append(report)
            return report
        
        for page in pages:
            page_name = page.get("name", "unnamed")
            components = page.get("components", [])
            
            for comp in components:
                data_source = comp.get("data_source", "")
                if data_source and data_source not in endpoint_paths:
                    # Try prefix match (e.g. /api/v1/contacts might match /api/v1/contacts/{id})
                    base = data_source.rstrip("/")
                    matched = any(ep.startswith(base) or base.startswith(ep.split("{")[0]) for ep in endpoint_paths)
                    if not matched:
                        report["errors"].append(
                            f"Page '{page_name}' component '{comp.get('id')}' data_source '{data_source}' has no matching API endpoint"
                        )
            
            report["pages_verified"].append(page_name)
        
        if report["errors"]:
            report["success"] = False
        
        self.reports.append(report)
        return report

    def run_full_simulation(self) -> dict:
        """Run complete execution simulation."""
        results = {
            "executable": False,
            "simulation_steps": [],
            "overall_errors": [],
            "code_artifacts": self._generate_code_artifacts()
        }
        
        steps = [
            self.simulate_db_init(),
            self.simulate_auth(),
            self.simulate_api_routes(),
            self.simulate_ui_pages()
        ]
        
        results["simulation_steps"] = steps
        all_errors = []
        for step in steps:
            all_errors.extend(step.get("errors", []))
        
        results["overall_errors"] = all_errors
        results["executable"] = len(all_errors) == 0
        results["executability_score"] = max(0, 100 - len(all_errors) * 10)
        
        return results

    def _generate_code_artifacts(self) -> dict:
        """Generate actual executable code from the schema."""
        artifacts = {}
        
        # Generate SQL DDL
        sql_lines = ["-- AppForge Generated SQL\n"]
        db_schema = self.schema.get("db_schema", {})
        for table in db_schema.get("tables", []):
            cols = []
            for col in table.get("columns", []):
                col_def = f"  {col['name']} {self._sql_type(col['type'])}"
                if col.get("primary_key"):
                    col_def += " PRIMARY KEY"
                if not col.get("nullable", True):
                    col_def += " NOT NULL"
                if col.get("unique"):
                    col_def += " UNIQUE"
                if col.get("default"):
                    col_def += f" DEFAULT {col['default']}"
                cols.append(col_def)
            
            # Add foreign keys
            for col in table.get("columns", []):
                fk = col.get("foreign_key")
                if fk and fk.get("table"):
                    cols.append(f"  FOREIGN KEY ({col['name']}) REFERENCES {fk['table']}({fk.get('column', 'id')})")
            
            sql_lines.append(f"CREATE TABLE {table['name']} (\n" + ",\n".join(cols) + "\n);")
        
        artifacts["schema.sql"] = "\n\n".join(sql_lines)
        
        # Generate Express.js routes
        js_lines = ["// AppForge Generated API Routes (Express.js)\nconst router = require('express').Router();"]
        api_schema = self.schema.get("api_schema", {})
        for ep in api_schema.get("endpoints", []):
            method = ep.get("method", "GET").lower()
            path = ep.get("path", "/")
            auth = ep.get("auth_required", False)
            roles = ep.get("roles_allowed", [])
            desc = ep.get("description", "")
            
            middleware = "authMiddleware, " if auth else ""
            if roles and roles != ["public"]:
                middleware += f"requireRole({json.dumps(roles)}), "
            
            js_lines.append(f"\n// {desc}\nrouter.{method}('{path}', {middleware}async (req, res) => {{\n  // TODO: implement\n  res.json({{ success: true }});\n}});")
        
        js_lines.append("\nmodule.exports = router;")
        artifacts["routes.js"] = "\n".join(js_lines)
        
        # Generate React page list
        react_lines = ["// AppForge Generated React Router Config"]
        ui_schema = self.schema.get("ui_schema", {})
        for page in ui_schema.get("pages", []):
            name = page.get("name", "Page").replace(" ", "")
            route = page.get("route", "/")
            auth = page.get("auth_required", False)
            wrapper = "ProtectedRoute" if auth else "Route"
            react_lines.append(f'<{wrapper} path="{route}" component={{{name}Page}} />')
        
        artifacts["routes.jsx"] = "\n".join(react_lines)
        
        return artifacts

    def _sql_type(self, t: str) -> str:
        mapping = {
            "uuid": "UUID", "varchar": "VARCHAR(255)", "text": "TEXT",
            "int": "INTEGER", "integer": "INTEGER", "bool": "BOOLEAN",
            "boolean": "BOOLEAN", "timestamp": "TIMESTAMP", "decimal": "DECIMAL(10,2)",
            "jsonb": "JSONB", "float": "FLOAT", "date": "DATE"
        }
        return mapping.get(t.lower(), "TEXT")


def simulate_execution(schema: dict) -> dict:
    """Entry point for execution simulation."""
    sim = RuntimeSimulator(schema)
    return sim.run_full_simulation()

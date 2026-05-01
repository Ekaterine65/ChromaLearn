import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = ROOT / "grafana" / "provisioning" / "dashboards"


def dashboards():
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in DASHBOARD_DIR.glob("chromalearn-*.json")
    ]


def panel_targets(dashboard):
    for panel in dashboard["panels"]:
        for target in panel.get("targets", []):
            yield panel, target


def test_mysql_datasource_uses_read_only_reader():
    datasource = yaml.safe_load(
        (ROOT / "grafana" / "provisioning" / "datasources" / "mysql.yml").read_text(
            encoding="utf-8"
        )
    )["datasources"][0]
    grant_script = (ROOT / "docker" / "mysql" / "init" / "01-grafana-reader.sh").read_text(
        encoding="utf-8"
    )

    assert datasource["uid"] == "chromalearn-mysql"
    assert datasource["user"] == "${GRAFANA_MYSQL_USER}"
    assert datasource["secureJsonData"]["password"] == "${GRAFANA_MYSQL_PASSWORD}"
    assert "GRANT SELECT ON" in grant_script
    assert "GRAFANA_MYSQL_PASSWORD" in grant_script
    assert "GRANT ALL" not in grant_script.upper()


def test_all_dashboard_queries_use_mysql_datasource_and_read_queries():
    for dashboard in dashboards():
        for panel, target in panel_targets(dashboard):
            assert panel["datasource"]["uid"] == "chromalearn-mysql"
            sql = target["rawSql"].strip().upper()
            assert sql.startswith("SELECT ")
            assert not any(keyword in sql for keyword in ("INSERT ", "UPDATE ", "DELETE ", "DROP "))


def test_time_series_queries_are_time_filtered():
    for dashboard in dashboards():
        for panel, target in panel_targets(dashboard):
            if target.get("format") == "time_series":
                sql = target["rawSql"]
                assert "$__timeGroupAlias" in sql
                assert "$__timeFilter" in sql


def test_grafana_nginx_proxy_requires_flask_admin_auth():
    nginx_conf = (ROOT / "nginx" / "default.conf").read_text(encoding="utf-8")

    assert "auth_request /admin/grafana-auth;" in nginx_conf
    assert "proxy_set_header X-WEBAUTH-USER $auth_user;" in nginx_conf


def test_task_dashboards_do_not_rank_empty_tasks_as_hardest():
    overview = json.loads(
        (DASHBOARD_DIR / "chromalearn-overview.json").read_text(encoding="utf-8")
    )
    tasks = json.loads(
        (DASHBOARD_DIR / "chromalearn-tasks.json").read_text(encoding="utf-8")
    )

    overview_hardest_sql = next(
        target["rawSql"]
        for panel, target in panel_targets(overview)
        if panel["title"] == "Hardest tasks"
    )
    task_performance_sql = next(
        target["rawSql"]
        for panel, target in panel_targets(tasks)
        if panel["title"] == "Task performance"
    )

    assert "JOIN results" in overview_hardest_sql
    assert "LEFT JOIN results" not in overview_hardest_sql
    assert "JOIN results" in task_performance_sql
    assert "LEFT JOIN results" not in task_performance_sql

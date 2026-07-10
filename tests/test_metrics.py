import pandas as pd

from database.connection import connect
from database.repository import save_telemetry_events
from analytics.metrics import total_events


def test_total_events():
    connection = connect(":memory:")

    df = pd.DataFrame(
        [
            {
                "event_id": "1",
                "event_timestamp": "2026-01-01 10:00:00",
                "event_date": "2026-01-01",
                "event_name": "api_request",
                "session_id": "session-1",
                "user_email": "test@example.com",
            }
        ]
    )

    save_telemetry_events(connection, df)

    result = total_events(connection)

    assert result.iloc[0]["total_events"] == 1

    connection.close()
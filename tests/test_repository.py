import pandas as pd

from database.connection import connect
from database.repository import save_employees, count_rows


def test_save_employees():
    connection = connect(":memory:")

    employees = pd.DataFrame(
        [
            {
                "email": "test@example.com",
                "full_name": "Test User",
                "practice": "AI",
                "level": "Junior",
                "location": "Ukraine",
            }
        ]
    )

    inserted = save_employees(connection, employees)

    assert inserted == 1
    assert count_rows(connection, "employees") == 1

    connection.close()
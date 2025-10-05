import click
import csv
from enum import Enum as PyEnum
from sqlalchemy import (
    Boolean,
    Column,
    create_engine,
    Enum,
    Float,
    insert,
    Integer,
    MetaData,
    String,
    Table,
)


@click.command()
@click.option(
    "--data_file",
    required=True,
    help="Path to the csv data file.",
)
@click.option(
    "--db_name",
    default="database",
    show_default=True,
    help="Name of the sqlite database.",
)
def create_db(data_file: str, db_name: str):
    db_path = f"data/{db_name}.db"
    engine = create_engine(f"sqlite:///{db_path}")
    metadata_obj = MetaData()

    class Gender(PyEnum):
        FEMALE = "female"
        MALE = "male"

    class ShippingType(PyEnum):
        TWO_DAY_SHIPPING = "2_day_shipping"
        EXPRESS = "express"
        FREE_SHIPPING = "free_shipping"
        NEXT_DAY_AIR = "next_day_air"
        STANDARD = "standard"
        STORE_PICKUP = "store_pickup"

    class PaymentMethod(PyEnum):
        BANK_TRANSFER = "bank_transfer"
        CASH = "cash"
        CREDIT_CARD = "credit_card"
        DEBIT_CARD = "debit_card"
        PAYPAL = "paypal"
        VENMO = "venmo"

    class FrequencyOfPurchases(PyEnum):
        ANNUALLY = "annually"
        BI_WEEKLY = "bi_weekly"
        MONTHLY = "monthly"
        EVERY_3_MONTHS = "every_3_months"
        FORTNIGHTLY = "fortnightly"
        QUARTERLY = "quarterly"
        WEEKLY = "weekly"

    def normalize_string(string):
        return string.lower().replace(" ", "_").replace("-", "_")

    # create SQL table
    table_name = "purchases"
    purchases_table = Table(
        table_name,
        metadata_obj,
        Column("customer_id", Integer, primary_key=True),
        Column("age", Integer),
        Column("gender", Enum(Gender)),
        Column("item_purchased", String, nullable=False),
        Column("category", String),
        Column("purchase_amount", Integer),
        Column("location", String),
        Column("size", String(1)),
        Column("color", String),
        Column("season", String),
        Column("review_rating", Float),
        Column("subscription_status", Boolean),
        Column("shipping_type", Enum(ShippingType)),
        Column("discount_applied", Boolean),
        Column("promo_code_used", Boolean),
        Column("previous_purchases", Integer),
        Column("payment_method", Enum(PaymentMethod)),
        Column("frequency_of_purchases", Enum(FrequencyOfPurchases)),
    )
    metadata_obj.create_all(engine)

    # read CSV
    with open(data_file, mode="r") as file:
        reader = csv.DictReader(file)
        data = []
        for row in reader:
            row["customer_id"] = int(row["customer_id"])
            row["age"] = int(row["age"])
            row["purchase_amount"] = int(row["purchase_amount"])
            row["previous_purchases"] = int(row["previous_purchases"])
            row["review_rating"] = float(row["review_rating"])
            row["gender"] = Gender(normalize_string(row["gender"]))
            row["shipping_type"] = ShippingType(normalize_string(row["shipping_type"]))
            row["payment_method"] = PaymentMethod(
                normalize_string(row["payment_method"])
            )
            row["frequency_of_purchases"] = FrequencyOfPurchases(
                normalize_string(row["frequency_of_purchases"])
            )
            row["subscription_status"] = row["subscription_status"] is True
            row["discount_applied"] = row["discount_applied"] is True
            row["promo_code_used"] = row["promo_code_used"] is True

            data.append(row)

        with engine.connect() as conn:
            transaction = conn.begin()
            conn.execute(insert(purchases_table), data)
            transaction.commit()
        print(f"Database saved as: {db_path}")


if __name__ == "__main__":
    create_db()

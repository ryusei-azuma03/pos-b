from sqlalchemy.orm import Session
from app import engine, SessionLocal, Product

# データベースの初期化
def insert_sample_data():
    db: Session = SessionLocal()
    sample_products = [
        {"code": "490177723311", "name": "コカ・コーラ", "price": 150},
        {"code": "490141105478", "name": "ペプシコーラ", "price": 140},
        {"code": "490130617298", "name": "お茶", "price": 120},
        {"code": "490123456789", "name": "ミネラルウォーター", "price": 100},
        {"code": "490987654321", "name": "オレンジジュース", "price": 130},
    ]

    for product in sample_products:
        db_product = Product(code=product["code"], name=product["name"], price=product["price"])
        db.add(db_product)

    db.commit()
    db.close()
    print("サンプルデータを追加しました。")

if __name__ == "__main__":
    insert_sample_data()

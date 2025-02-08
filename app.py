from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, relationship, declarative_base, Session
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# Azure MySQLのデータベースURLを環境変数から取得
DATABASE_URL = os.getenv("DB_URL", "sqlite:///./test.db")  # デフォルトはSQLite

# Database setup
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class Product(Base):
    __tablename__ = "m_product_azu"  # Azure MySQL のテーブル名に修正

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(13), unique=True, nullable=False)
    name = Column(String(50), nullable=False)
    price = Column(Float, nullable=False)

class Transaction(Base):
    __tablename__ = "m_transaction_azu"  # Azure MySQL のテーブル名に修正

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    total_amount = Column(Float, nullable=False)
    details = relationship("TransactionDetail", back_populates="transaction")

class TransactionDetail(Base):
    __tablename__ = "m_transaction_detail_azu"  # Azure MySQL のテーブル名に修正

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("m_transaction_azu.id"), nullable=False)  # 修正
    product_id = Column(Integer, ForeignKey("m_product_azu.id"), nullable=False)  # 修正
    quantity = Column(Integer, nullable=False)
    subtotal = Column(Float, nullable=False)

    transaction = relationship("Transaction", back_populates="details")
    product = relationship("Product")

# Create tables
Base.metadata.create_all(bind=engine)

# FastAPI app setup
app = FastAPI()

# CORS 設定追加（フロントエンドを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://tech0-gen8-step4-pos-app-67.azurewebsites.net"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
class ProductRequest(BaseModel):
    code: str

class ProductResponse(BaseModel):
    id: int
    code: str
    name: str
    price: float

    class Config:
        from_attributes = True

class TransactionRequest(BaseModel):
    product_ids: List[int]
    quantities: List[int]

class TransactionResponse(BaseModel):
    id: int
    timestamp: str
    total_amount: float

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=obj.id,
            timestamp=obj.timestamp.isoformat(),
            total_amount=obj.total_amount
        )

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Routes
@app.post("/products/search", response_model=ProductResponse)
def search_product(request: ProductRequest, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.code == request.code).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.get("/products/all", response_model=List[ProductResponse])
def get_all_products(db: Session = Depends(get_db)):
    """全商品を取得"""
    return db.query(Product).all()

@app.post("/transactions", response_model=TransactionResponse)
def create_transaction(request: TransactionRequest, db: Session = Depends(get_db)):
    if len(request.product_ids) != len(request.quantities):
        raise HTTPException(status_code=400, detail="Product IDs and quantities must match in length")

    total_amount = 0
    details = []

    for product_id, quantity in zip(request.product_ids, request.quantities):
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product ID {product_id} not found")
        subtotal = product.price * quantity
        total_amount += subtotal

        detail = TransactionDetail(product_id=product.id, quantity=quantity, subtotal=subtotal)
        details.append(detail)

    transaction = Transaction(total_amount=total_amount, details=details)
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return TransactionResponse.from_orm(transaction)

@app.get("/transactions/all", response_model=List[TransactionResponse])
def get_all_transactions(db: Session = Depends(get_db)):
    """全取引履歴を取得"""
    return [TransactionResponse.from_orm(t) for t in db.query(Transaction).all()]

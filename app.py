from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, relationship, declarative_base, Session
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware

# Database setup
DATABASE_URL = "sqlite:///./test.db"  # SQLite for simplicity
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()  # 修正: `sqlalchemy.orm.declarative_base()` を使用

# Database Models
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(13), unique=True, nullable=False)
    name = Column(String(50), nullable=False)
    price = Column(Float, nullable=False)

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    total_amount = Column(Float, nullable=False)
    details = relationship("TransactionDetail", back_populates="transaction")

class TransactionDetail(Base):
    __tablename__ = "transaction_details"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    subtotal = Column(Float, nullable=False)

    transaction = relationship("Transaction", back_populates="details")
    product = relationship("Product")

# Create tables
Base.metadata.create_all(bind=engine)

# FastAPI app setup
app = FastAPI()

# CORS 設定追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # フロントエンドのURLを明示的に指定
    allow_credentials=True,
    allow_methods=["*"],  # すべてのHTTPメソッドを許可
    allow_headers=["*"],  # すべてのヘッダーを許可
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
        from_attributes = True  # 修正: `orm_mode` → `from_attributes`

class TransactionRequest(BaseModel):
    product_ids: List[int]
    quantities: List[int]

class TransactionResponse(BaseModel):
    id: int
    timestamp: str
    total_amount: float

    class Config:
        from_attributes = True  # 修正

    @classmethod
    def from_orm(cls, obj):
        """データベースの ORM オブジェクトから `TransactionResponse` を生成"""
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
    try:
        product = db.query(Product).filter(Product.code == request.code).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products/all", response_model=List[ProductResponse])
def get_all_products(db: Session = Depends(get_db)):
    """登録されている全商品を取得する"""
    try:
        products = db.query(Product).all()
        return products
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transactions", response_model=TransactionResponse)
def create_transaction(request: TransactionRequest, db: Session = Depends(get_db)):
    if len(request.product_ids) != len(request.quantities):
        raise HTTPException(status_code=400, detail="Product IDs and quantities must match in length")

    try:
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/transactions/all", response_model=List[TransactionResponse])
def get_all_transactions(db: Session = Depends(get_db)):
    """登録されている全取引履歴を取得する"""
    try:
        transactions = db.query(Transaction).all()
        return [TransactionResponse.from_orm(t) for t in transactions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

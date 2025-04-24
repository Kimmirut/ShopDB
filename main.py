from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import Column, Integer, String, Float, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import List
from pydantic import BaseModel

DATABASE_URL = "mysql+pymysql://user:password@localhost:3306/shop_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI()

# Модель товара
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    price = Column(Float)
    description = Column(String(255))
    stock = Column(Integer)

# Pydantic-схемы
class ProductCreate(BaseModel):
    name: str
    price: float
    description: str
    stock: int

class ProductUpdate(BaseModel):
    name: str | None = None
    price: float | None = None
    description: str | None = None
    stock: int | None = None

class ProductOut(ProductCreate):
    id: int

    class Config:
        orm_mode = True

# Зависимость

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Инициализация таблицы
Base.metadata.create_all(bind=engine)

# Роуты для товаров
@app.post("/products/", response_model=ProductOut)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.get("/products/", response_model=List[ProductOut])
def read_products(db: Session = Depends(get_db)):
    return db.query(Product).all()

@app.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"ok": True}

@app.put("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, product_data: ProductUpdate, db: Session = Depends(get_db)):
    product = db.query(Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    update_data = product_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product

# Простая корзина (в памяти)
cart = []

@app.post("/cart/{product_id}")
def add_to_cart(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    cart.append(product)
    return {"msg": f"Product {product.name} added to cart"}

@app.get("/cart/", response_model=List[ProductOut])
def view_cart():
    return cart

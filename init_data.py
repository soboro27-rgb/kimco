from database import SessionLocal, engine
import models
import bcrypt

models.Base.metadata.create_all(bind=engine)

db = SessionLocal()

if not db.query(models.User).filter(models.User.username == "superadmin").first():
    pw = bcrypt.hashpw("super1234".encode(), bcrypt.gensalt()).decode()
    db.add(models.User(username="superadmin", password_hash=pw, name="통합관리자", role="superadmin"))
    db.commit()
    print("통합관리자 생성: superadmin / super1234")

if not db.query(models.User).filter(models.User.username == "admin").first():
    pw = bcrypt.hashpw("admin1234".encode(), bcrypt.gensalt()).decode()
    db.add(models.User(username="admin", password_hash=pw, name="담당자1", role="admin"))
    db.commit()
    print("담당자 생성: admin / admin1234")

db.close()

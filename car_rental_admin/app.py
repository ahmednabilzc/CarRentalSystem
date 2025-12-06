from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime

app = Flask(__name__)

# ===== إعدادات الـ Database =====
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///car_rental.db"  # ملف DB في نفس الفولدر
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# ===== Model: Car =====
class Car(db.Model):
    __tablename__ = "cars"

    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    car_type = db.Column(db.String(50), nullable=False)        # مثلا: Sedan / SUV
    rental_rate = db.Column(db.Float, nullable=False)          # السعر في اليوم
    availability_status = db.Column(db.String(20), default="Available")  # Available / Rented

    # علاقة مع الصيانة
    maintenance_records = db.relationship("Maintenance", backref="car", lazy=True)

    def __repr__(self):
        return f"<Car {self.id} - {self.brand} {self.model}>"


# ===== Model: Maintenance =====
class Maintenance(db.Model):
    __tablename__ = "maintenance"

    id = db.Column(db.Integer, primary_key=True)
    car_id = db.Column(db.Integer, db.ForeignKey("cars.id"), nullable=False)
    service_type = db.Column(db.String(100), nullable=False)   # Oil change, Tires, ...
    cost = db.Column(db.Float, nullable=False)
    service_date = db.Column(db.Date, nullable=False, default=date.today)
    notes = db.Column(db.Text)

    def __repr__(self):
        return f"<Maintenance {self.id} - Car {self.car_id}>"


# ===== إنشاء الجداول + إضافة داتا تجريبية لو الـ DB فاضية =====
with app.app_context():
    db.create_all()  # ينشئ جداول cars و maintenance لو مش موجودة

    if Car.query.count() == 0:
        sample_cars = [
            Car(brand="Toyota", model="Corolla", car_type="Sedan", rental_rate=300, availability_status="Available"),
            Car(brand="Hyundai", model="Elantra", car_type="Sedan", rental_rate=280, availability_status="Rented"),
            Car(brand="Kia", model="Sportage", car_type="SUV", rental_rate=400, availability_status="Available"),
        ]
        db.session.add_all(sample_cars)
        db.session.commit()
        print("Sample cars inserted into database.")


# ===== Routes =====

# ---------- Admin Dashboard ----------
@app.route("/admin")
def admin_dashboard():
    total_cars = Car.query.count()
    available_cars = Car.query.filter_by(availability_status="Available").count()
    rented_cars = Car.query.filter_by(availability_status="Rented").count()
    total_maintenance = Maintenance.query.count()

    return render_template(
        "dashboard.html",
        total_cars=total_cars,
        available_cars=available_cars,
        rented_cars=rented_cars,
        total_maintenance=total_maintenance,
    )


# ---------- Cars CRUD (FR-2.0) ----------
@app.route("/admin/cars")
def admin_cars():
    cars = Car.query.all()
    return render_template("cars.html", cars=cars)


@app.route("/admin/cars/new", methods=["GET", "POST"])
def new_car():
    if request.method == "POST":
        brand = request.form.get("brand")
        model = request.form.get("model")
        car_type = request.form.get("car_type")
        rental_rate = request.form.get("rental_rate")
        availability_status = request.form.get("availability_status")

        if not brand or not model or not car_type or not rental_rate:
            return "Please fill all required fields"

        car = Car(
            brand=brand,
            model=model,
            car_type=car_type,
            rental_rate=float(rental_rate),
            availability_status=availability_status,
        )
        db.session.add(car)
        db.session.commit()

        return redirect("/admin/cars")

    return render_template("car_form.html")


@app.route("/admin/cars/<int:car_id>/edit", methods=["GET", "POST"])
def edit_car(car_id):
    car = Car.query.get_or_404(car_id)

    if request.method == "POST":
        car.brand = request.form.get("brand")
        car.model = request.form.get("model")
        car.car_type = request.form.get("car_type")
        car.rental_rate = float(request.form.get("rental_rate"))
        car.availability_status = request.form.get("availability_status")

        db.session.commit()
        return redirect("/admin/cars")

    return render_template("edit_car_form.html", car=car)


@app.route("/admin/cars/<int:car_id>/delete", methods=["POST"])
def delete_car(car_id):
    car = Car.query.get_or_404(car_id)
    db.session.delete(car)
    db.session.commit()
    return redirect("/admin/cars")


# ---------- Maintenance (FR-5.0) ----------
@app.route("/admin/maintenance")
def maintenance_list():
    records = Maintenance.query.order_by(Maintenance.service_date.desc()).all()
    return render_template("maintenance.html", records=records)


@app.route("/admin/maintenance/new", methods=["GET", "POST"])
def new_maintenance():
    cars = Car.query.all()

    if request.method == "POST":
        car_id = request.form.get("car_id")
        service_type = request.form.get("service_type")
        cost = request.form.get("cost")
        service_date_str = request.form.get("service_date")
        notes = request.form.get("notes")

        if not car_id or not service_type or not cost or not service_date_str:
            return "Please fill all required fields"

        service_date = datetime.strptime(service_date_str, "%Y-%m-%d").date()

        record = Maintenance(
            car_id=int(car_id),
            service_type=service_type,
            cost=float(cost),
            service_date=service_date,
            notes=notes,
        )
        db.session.add(record)
        db.session.commit()

        return redirect("/admin/maintenance")

    return render_template("maintenance_form.html", cars=cars)


# ---------- Reports (FR-6.0) ----------
@app.route("/admin/reports", methods=["GET", "POST"])
def reports():
    if request.method == "POST":
        report_type = request.form.get("report_type")
        date_from_str = request.form.get("date_from")
        date_to_str = request.form.get("date_to")

        date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date() if date_from_str else None
        date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date() if date_to_str else None

        if report_type == "car_summary":
            total_cars = Car.query.count()
            available_cars = Car.query.filter_by(availability_status="Available").count()
            rented_cars = Car.query.filter_by(availability_status="Rented").count()

            return render_template(
                "report_result.html",
                report_type="car_summary",
                total_cars=total_cars,
                available_cars=available_cars,
                rented_cars=rented_cars,
                date_from=date_from,
                date_to=date_to,
            )

        elif report_type == "maintenance_summary":
            query = Maintenance.query
            if date_from:
                query = query.filter(Maintenance.service_date >= date_from)
            if date_to:
                query = query.filter(Maintenance.service_date <= date_to)

            records = query.all()
            total_operations = len(records)
            total_cost = sum(r.cost for r in records)

            return render_template(
                "report_result.html",
                report_type="maintenance_summary",
                total_operations=total_operations,
                total_cost=total_cost,
                date_from=date_from,
                date_to=date_to,
            )

        else:
            return "Invalid report type"

    # GET
    return render_template("reports.html")


if __name__ == "__main__":
    app.run(debug=True)

from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3

def get_db_connection():
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row
    return conn

app = Flask(__name__)

app.secret_key = "sample-secret-key"

@app.route("/")
def home():

    conn = get_db_connection()

    products = conn.execute(
        "SELECT * FROM products"
    ).fetchall()

    conn.close()

    products = [
        {
            "id": product["id"],
            "name": product["name"],
            "stock": product["stock"],
            "proper_stock": product["proper_stock"],
            "difference": product["stock"] - product["proper_stock"]
        }
        for product in products
    ]

    return render_template(
        "index.html",
        products=products
    )

@app.route("/transaction", methods=["GET", "POST"])
def transaction():

    if request.method == "POST":
        product_id = int(request.form["product_id"])
        transaction_type = request.form["transaction_type"]
        quantity = int(request.form["quantity"])

        

        # 0以下は登録できない
        if quantity <= 0:
            flash("数量は1以上を入力してください")
            return redirect(url_for("transaction"))

        conn = get_db_connection()
        product = conn.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        if product is not None:
            if transaction_type == "in":
                conn.execute(
                    "UPDATE products SET stock = stock + ? WHERE id = ?",
                    (quantity, product_id)
                )
                conn.commit()
                flash("入荷を登録しました")

            elif transaction_type == "out":
                if quantity > product["stock"]:
                    conn.close()
                    flash("在庫数を超える出庫はできません")
                    return redirect(url_for("transaction"))

                conn.execute(
                    "UPDATE products SET stock = stock - ? WHERE id = ?",
                    (quantity, product_id)
                )
                conn.commit()
                flash("出庫を登録しました")

        conn.close()

        return redirect(url_for("home"))

    conn = get_db_connection()
    products = conn.execute(
        "SELECT * FROM products"
    ).fetchall()
    conn.close()

    return render_template(
        "transaction.html",
        products=products
    )

@app.route("/product/add", methods=["GET", "POST"])
def add_product_master():

    if request.method == "POST":
        name = request.form["name"]
        proper_stock = request.form["proper_stock"]

        if name == "" or proper_stock == "":
            flash("商品名と適正在庫を入力してください")
            return redirect(url_for("add_product_master"))

        proper_stock = int(proper_stock)

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO products (name, stock, proper_stock)
            VALUES (?, ?, ?)
            """,
            (name, 0, proper_stock)
        )
        conn.commit()
        conn.close()

        flash("商品を追加しました")
        return redirect(url_for("home"))

    conn = get_db_connection()
    products = conn.execute(
        "SELECT * FROM products"
    ).fetchall()
    conn.close()

    return render_template(
        "product_add.html",
        products=products
    )

@app.route("/product/delete/<int:product_id>", methods=["POST"])
def delete_product(product_id):

    conn = get_db_connection()
    conn.execute(
        "DELETE FROM products WHERE id = ?",
        (product_id,)
    )
    conn.commit()
    conn.close()

    flash("商品を削除しました")
    return redirect(url_for("add_product_master"))
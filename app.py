from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime

UNIT_OPTIONS = ["袋", "本", "個", "箱", "缶", "パック", "kg", "g", "L", "ml", "その他"]

def get_db_connection():
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row
    product_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(products)")
    }
    if product_columns and "unit" not in product_columns:
        conn.execute("ALTER TABLE products ADD COLUMN unit TEXT")
        conn.commit()
    columns = {
        row[1] for row in conn.execute("PRAGMA table_info(transactions)")
    }
    if columns and "product_id" not in columns:
        conn.execute("ALTER TABLE transactions ADD COLUMN product_id INTEGER")
        conn.commit()
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
            "unit": product["unit"],
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
                conn.execute(
                    """
                    INSERT INTO transactions (product_id, product_name, transaction_type, quantity, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (product_id, product["name"], "入荷", quantity, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
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
                conn.execute(
                    """
                    INSERT INTO transactions (product_id, product_name, transaction_type, quantity, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (product_id, product["name"], "出庫", quantity, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
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

@app.route("/history")
def history():

    conn = get_db_connection()
    transactions = conn.execute(
        """
        SELECT transactions.*, products.name AS current_product_name,
             products.unit AS current_product_unit
        FROM transactions
        LEFT JOIN products ON products.id = transactions.product_id
        ORDER BY transactions.id DESC
        """
    ).fetchall()
    conn.close()

    return render_template(
        "history.html",
        transactions=transactions
    )

def transaction_effect(transaction_type, quantity):
    if transaction_type in ("in", "入荷"):
        return quantity
    return -quantity

def transaction_label(transaction_type):
    if transaction_type in ("in", "入荷"):
        return "入庫"
    return "出庫"

def transaction_form_value(transaction_type):
    if transaction_type in ("in", "入荷"):
        return "in"
    return "out"

def get_transaction_product(conn, transaction):
    if transaction["product_id"] is not None:
        return conn.execute(
            "SELECT * FROM products WHERE id = ?",
            (transaction["product_id"],)
        ).fetchone()
    return conn.execute(
        "SELECT * FROM products WHERE name = ? ORDER BY id LIMIT 1",
        (transaction["product_name"],)
    ).fetchone()

@app.route("/history/edit/<int:transaction_id>", methods=["GET", "POST"])
def edit_transaction(transaction_id):

    conn = get_db_connection()
    transaction_record = conn.execute(
        "SELECT * FROM transactions WHERE id = ?",
        (transaction_id,)
    ).fetchone()

    if transaction_record is None:
        conn.close()
        flash("履歴が見つかりません")
        return redirect(url_for("history"))

    if request.method == "POST":
        product_id = int(request.form["product_id"])
        transaction_type = request.form["transaction_type"]
        quantity = int(request.form["quantity"])
        created_at = request.form["created_at"]

        if quantity <= 0:
            conn.close()
            flash("数量は1以上を入力してください")
            return redirect(url_for("edit_transaction", transaction_id=transaction_id))

        old_product = get_transaction_product(conn, transaction_record)
        new_product = conn.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        if old_product is None or new_product is None:
            conn.close()
            flash("商品が見つかりません")
            return redirect(url_for("edit_transaction", transaction_id=transaction_id))

        try:
            if created_at:
                created_at = datetime.fromisoformat(created_at).strftime("%Y-%m-%d %H:%M:%S")
            else:
                created_at = transaction_record["created_at"]
        except ValueError:
            conn.close()
            flash("日時の形式が正しくありません")
            return redirect(url_for("edit_transaction", transaction_id=transaction_id))

        old_effect = transaction_effect(transaction_record["transaction_type"], transaction_record["quantity"])
        new_effect = transaction_effect(transaction_type, quantity)
        old_stock_after_reversal = old_product["stock"] - old_effect
        new_stock_after_update = old_stock_after_reversal + new_effect if old_product["id"] == new_product["id"] else new_product["stock"] + new_effect

        if old_product["id"] != new_product["id"] and new_stock_after_update < 0:
            conn.close()
            flash("在庫数が不足しているため更新できません")
            return redirect(url_for("edit_transaction", transaction_id=transaction_id))
        if old_product["id"] == new_product["id"] and new_stock_after_update < 0:
            conn.close()
            flash("在庫数が不足しているため更新できません")
            return redirect(url_for("edit_transaction", transaction_id=transaction_id))

        conn.execute(
            "UPDATE products SET stock = stock - ? WHERE id = ?",
            (old_effect, old_product["id"])
        )
        if old_product["id"] == new_product["id"]:
            conn.execute(
                "UPDATE products SET stock = stock + ? WHERE id = ?",
                (new_effect, new_product["id"])
            )
        else:
            conn.execute(
                "UPDATE products SET stock = stock + ? WHERE id = ?",
                (new_effect, new_product["id"])
            )

        conn.execute(
            """
            UPDATE transactions
            SET product_id = ?, product_name = ?, transaction_type = ?, quantity = ?, created_at = ?
            WHERE id = ?
            """,
            (new_product["id"], new_product["name"], "入荷" if transaction_type == "in" else "出庫", quantity, created_at, transaction_id)
        )
        conn.commit()
        conn.close()
        flash("履歴を更新しました")
        return redirect(url_for("history"))

    products = conn.execute("SELECT * FROM products ORDER BY id").fetchall()
    product = get_transaction_product(conn, transaction_record)
    conn.close()
    return render_template(
        "history_edit.html",
        transaction=transaction_record,
        products=products,
        product=product,
        transaction_label=transaction_label,
        transaction_form_value=transaction_form_value
    )

@app.route("/history/delete/<int:transaction_id>", methods=["POST"])
def delete_transaction(transaction_id):

    conn = get_db_connection()
    transaction_record = conn.execute(
        "SELECT * FROM transactions WHERE id = ?",
        (transaction_id,)
    ).fetchone()
    if transaction_record is None:
        conn.close()
        flash("履歴が見つかりません")
        return redirect(url_for("history"))

    product = get_transaction_product(conn, transaction_record)
    if product is None:
        conn.close()
        flash("商品が見つからないため履歴を削除できません")
        return redirect(url_for("history"))

    effect = transaction_effect(transaction_record["transaction_type"], transaction_record["quantity"])
    if product["stock"] - effect < 0:
        conn.close()
        flash("在庫数が不足しているため削除できません")
        return redirect(url_for("history"))

    conn.execute(
        "UPDATE products SET stock = stock - ? WHERE id = ?",
        (effect, product["id"])
    )
    conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    conn.commit()
    conn.close()
    flash("履歴を削除しました")
    return redirect(url_for("history"))

@app.route("/product/add", methods=["GET", "POST"])
def add_product_master():

    if request.method == "POST":
        name = request.form["name"]
        unit = request.form.get("unit", "") or None
        proper_stock = request.form["proper_stock"]

        if name == "" or proper_stock == "":
            flash("商品名と適正在庫を入力してください")
            return redirect(url_for("add_product_master"))

        proper_stock = int(proper_stock)

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO products (name, stock, proper_stock, unit)
            VALUES (?, ?, ?, ?)
            """,
            (name, 0, proper_stock, unit)
        )
        conn.commit()
        conn.close()

        flash("商品を追加しました")
        return redirect(url_for("product_list"))

    conn = get_db_connection()
    products = conn.execute(
        "SELECT * FROM products"
    ).fetchall()
    conn.close()

    return render_template(
        "product_add.html",
        products=products,
        unit_options=UNIT_OPTIONS
    )

@app.route("/products")
def product_list():

    conn = get_db_connection()
    products = conn.execute(
        "SELECT * FROM products ORDER BY id"
    ).fetchall()
    conn.close()

    return render_template(
        "product_list.html",
        products=products
    )

@app.route("/product/edit/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):

    conn = get_db_connection()
    product = conn.execute(
        "SELECT * FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    if product is None:
        conn.close()
        flash("商品が見つかりません")
        return redirect(url_for("product_list"))

    if request.method == "POST":
        name = request.form["name"]
        unit = request.form.get("unit", "") or None
        proper_stock = request.form["proper_stock"]

        if name == "" or proper_stock == "":
            conn.close()
            flash("商品名と適正在庫を入力してください")
            return redirect(url_for("edit_product", product_id=product_id))

        proper_stock = int(proper_stock)
        conn.execute(
            "UPDATE products SET name = ?, proper_stock = ?, unit = ? WHERE id = ?",
            (name, proper_stock, unit, product_id)
        )
        conn.commit()
        conn.close()

        flash("商品を更新しました")
        return redirect(url_for("product_list"))

    conn.close()
    return render_template(
        "product_edit.html",
        product=product,
        unit_options=UNIT_OPTIONS
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
    return redirect(url_for("product_list"))
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)

app.secret_key = "sample-secret-key"

products = [
    {"id": 1, "name": "コーヒー豆", "stock": 10, "proper_stock": 15},
    {"id": 2, "name": "ミルク", "stock": 5, "proper_stock": 8}
]

@app.route("/")
def home():

    for product in products:
        product["difference"] = product["stock"] - product["proper_stock"]

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

        for product in products:
            if product["id"] == product_id:

                if transaction_type == "in":
                    product["stock"] += quantity
                    flash("入荷を登録しました")

                elif transaction_type == "out":

                    if quantity > product["stock"]:
                        flash("在庫数を超える出庫はできません")
                        return redirect(url_for("transaction"))

                    

                    product["stock"] -= quantity
                    flash("出庫を登録しました")

                break

        return redirect(url_for("home"))

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

        new_id = max(product["id"] for product in products) + 1

        products.append({
            "id": new_id,
            "name": name,
            "stock": 0,
            "proper_stock": proper_stock
        })

        flash("商品を追加しました")
        return redirect(url_for("home"))

    return render_template("product_add.html")
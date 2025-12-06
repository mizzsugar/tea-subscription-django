from django import forms
from django.core.validators import MaxValueValidator


class AddToCartForm(forms.Form):
    """カートに追加フォーム"""

    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        label="数量",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control text-center quantity-input",
                "style": "max-width: 80px;",
            }
        ),
    )

    def __init__(self, *args, product=None, **kwargs):
        super().__init__(*args, **kwargs)
        if product:
            self.product = product
            # 在庫数を最大値に設定
            self.fields["quantity"].widget.attrs["max"] = product.stock
            self.fields["quantity"].validators.append(
                MaxValueValidator(
                    product.stock, message=f"在庫は{product.stock}個までです"
                )
            )

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]
        if hasattr(self, "product"):
            if quantity > self.product.stock:
                raise forms.ValidationError(
                    f"在庫が不足しています（在庫: {self.product.stock}個）"
                )
        return quantity


class UpdateCartItemForm(forms.Form):
    """カートアイテム更新フォーム"""

    quantity = forms.IntegerField(
        min_value=1,
        label="数量",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "style": "width: 80px;",
            }
        ),
    )

    def __init__(self, *args, cart_item=None, **kwargs):
        super().__init__(*args, **kwargs)
        if cart_item:
            self.cart_item = cart_item
            self.fields["quantity"].widget.attrs["max"] = cart_item.product.stock
            self.fields["quantity"].initial = cart_item.quantity

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]
        if hasattr(self, "cart_item"):
            if quantity > self.cart_item.product.stock:
                raise forms.ValidationError(
                    f"在庫が不足しています（在庫: {self.cart_item.product.stock}個）"
                )
        return quantity


class CheckoutForm(forms.Form):
    """チェックアウトフォーム"""

    shipping_name = forms.CharField(
        max_length=100,
        label="お名前",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "山田 太郎",
            }
        ),
    )
    shipping_postal_code = forms.CharField(
        max_length=8,
        label="郵便番号",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "123-4567",
            }
        ),
    )
    shipping_address = forms.CharField(
        label="住所",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "東京都渋谷区〇〇1-2-3 〇〇マンション101号室",
            }
        ),
    )
    shipping_phone = forms.CharField(
        max_length=20,
        label="電話番号",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "090-1234-5678",
            }
        ),
    )

    def clean_shipping_postal_code(self):
        postal_code = self.cleaned_data["shipping_postal_code"]
        # ハイフンを削除
        postal_code = postal_code.replace("-", "")
        # 7桁の数字かチェック
        if not postal_code.isdigit() or len(postal_code) != 7:
            raise forms.ValidationError(
                "郵便番号は7桁の数字で入力してください（例: 1234567 または 123-4567）"
            )
        # ハイフン付きで返す
        return f"{postal_code[:3]}-{postal_code[3:]}"

    def clean_shipping_phone(self):
        phone = self.cleaned_data["shipping_phone"]
        # ハイフンとスペースを削除
        phone_digits = (
            phone.replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
        )
        # 数字のみかチェック
        if not phone_digits.isdigit():
            raise forms.ValidationError("電話番号は数字で入力してください")
        # 10桁または11桁かチェック
        if len(phone_digits) not in [10, 11]:
            raise forms.ValidationError("電話番号は10桁または11桁で入力してください")
        return phone

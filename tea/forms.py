from django import forms

from model.models import TeaReview


class ReviewForm(forms.ModelForm):
    """レビューフォーム"""

    rating = forms.ChoiceField(
        choices=TeaReview.RATING_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="評価",
        initial=3,
    )

    class Meta:
        model = TeaReview
        fields = ["rating", "content"]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "レビューを入力してください",
                }
            ),
        }
        labels = {
            "content": "レビュー内容",
        }

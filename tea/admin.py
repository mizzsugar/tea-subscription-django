from django.contrib import admin
from tea.models import User, Tea, FavoriteTea, TeaReview

# Register your models here.
admin.site.register(User)
admin.site.register(Tea)
admin.site.register(FavoriteTea)
admin.site.register(TeaReview)

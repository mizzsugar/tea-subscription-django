from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
import stripe
import uuid
from model.models import Tea, TeaProduct,CartItem, Cart, Order, OrderItem, TaxRate

stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
@require_POST
def add_to_cart(request, product_id):
    """カートに追加"""
    product = get_object_or_404(TeaProduct, id=product_id, is_available=True)
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity < 1:
        messages.error(request, '数量は1以上を指定してください')
        return redirect('published_tea_detail', tea_id=product.tea.id)
    
    if product.stock < quantity:
        messages.error(request, '在庫が不足しています')
        return redirect('published_tea_detail', tea_id=product.tea.id)
    
    # カートを取得または作成
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # カートアイテムを取得または作成
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': quantity}
    )
    
    if not created:
        # 既存のアイテムの場合は数量を追加
        new_quantity = cart_item.quantity + quantity
        if product.stock < new_quantity:
            messages.error(request, '在庫が不足しています')
            return redirect('published_tea_detail', tea_id=product.tea.id)
        cart_item.quantity = new_quantity
        cart_item.save()
    
    messages.success(request, 'カートに追加しました')
    return redirect('shop:cart')


@login_required
def cart_view(request):
    """カート表示"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related('product__tea').all()
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
    }
    return render(request, 'shop/cart.html', context)


@login_required
@require_POST
def update_cart_item(request, item_id):
    """カートアイテムの数量更新"""
    cart_item = get_object_or_404(
        CartItem, 
        id=item_id, 
        cart__user=request.user
    )
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity < 1:
        cart_item.delete()
        messages.success(request, 'カートから削除しました')
    else:
        if cart_item.product.stock < quantity:
            messages.error(request, '在庫が不足しています')
        else:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, '数量を更新しました')
    
    return redirect('shop:cart')


@login_required
@require_POST
def remove_cart_item(request, item_id):
    """カートから削除"""
    cart_item = get_object_or_404(
        CartItem, 
        id=item_id, 
        cart__user=request.user
    )
    cart_item.delete()
    messages.success(request, 'カートから削除しました')
    return redirect('shop:cart')


@login_required
def checkout(request):
    """チェックアウト画面"""
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.select_related('product__tea').all()
    
    if not cart_items:
        messages.warning(request, 'カートが空です')
        return redirect('published_tea_list')
    
    # 在庫チェック
    for item in cart_items:
        if item.product.stock < item.quantity:
            messages.error(
                request, 
                f'{item.product}の在庫が不足しています'
            )
            return redirect('shop:cart')
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY,  # これを追加
    }
    print('=============')
    print(context)
    return render(request, 'shop/checkout.html', context)


@login_required
@require_POST
def create_checkout_session(request):
    """Stripe Checkout Sessionを作成"""
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.select_related('product__tea').all()
    
    if not cart_items:
        return JsonResponse({'error': 'カートが空です'}, status=400)
    
    # 配送先情報を取得
    shipping_data = {
        'shipping_name': request.POST.get('shipping_name'),
        'shipping_postal_code': request.POST.get('shipping_postal_code'),
        'shipping_address': request.POST.get('shipping_address'),
        'shipping_phone': request.POST.get('shipping_phone'),
    }
    tax_rate = TaxRate.get_current_rate()
    
    # 注文を作成（金額フィールドに初期値を設定）
    order = Order.objects.create(
        user=request.user,
        order_number=f'ORD-{uuid.uuid4().hex[:12].upper()}',
        subtotal=0,
        tax_amount=0,
        total_amount=0,
        shipping_fee=0,
        tax_rate=tax_rate,
        **shipping_data
    )
    
    # 注文明細を作成
    for cart_item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=cart_item.product,
            quantity=cart_item.quantity,
            price=cart_item.product.price,
        )
    
    # 金額を計算（注文明細作成後に実行）
    order.calculate_amounts()
    order.save()
    
    # Stripe line_itemsを作成
    line_items = []
    
    # 商品
    for cart_item in cart_items:
        line_items.append({
            'price_data': {
                'currency': 'jpy',
                'product_data': {
                    'name': f'{cart_item.product.tea.name} ({cart_item.product.weight}g)',
                    'description': cart_item.product.tea.description[:100] if cart_item.product.tea.description else '',
                },
                'unit_amount': cart_item.product.get_price_with_tax(),  # 税込価格
            },
            'quantity': cart_item.quantity,
        })
    
    # 送料
    if order.shipping_fee > 0:
        line_items.append({
            'price_data': {
                'currency': 'jpy',
                'product_data': {
                    'name': '送料',
                },
                'unit_amount': order.shipping_fee,
            },
            'quantity': 1,
        })
    
    try:
        # Checkout Sessionを作成
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=request.build_absolute_uri(
                reverse('shop:payment_success')
            ) + f'?session_id={{CHECKOUT_SESSION_ID}}&order_id={order.id}',
            cancel_url=request.build_absolute_uri(
                reverse('shop:payment_cancel')
            ) + f'?order_id={order.id}',
            customer_email=request.user.email,
            metadata={
                'order_id': order.id,
            }
        )
        
        # Checkout Session IDを保存
        order.stripe_checkout_session_id = checkout_session.id
        order.save()
        
        return JsonResponse({'sessionId': checkout_session.id})
        
    except Exception as e:
        order.delete()
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def payment_success(request):
    """支払い成功"""
    session_id = request.GET.get('session_id')
    order_id = request.GET.get('order_id')
    
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    try:
        # Stripeのセッション情報を取得
        session = stripe.checkout.Session.retrieve(session_id)
        
        if session.payment_status == 'paid':
            # 注文ステータスを更新
            order.status = 'paid'
            order.stripe_payment_intent_id = session.payment_intent
            order.save()
            
            # 在庫を減らす
            for item in order.items.all():
                product = item.product
                product.stock -= item.quantity
                product.save()
            
            # カートを空にする
            cart = Cart.objects.filter(user=request.user).first()
            if cart:
                cart.items.all().delete()
            
            messages.success(request, 'お支払いが完了しました')
        
    except Exception as e:
        messages.error(request, f'エラーが発生しました: {str(e)}')
    
    return redirect('shop:order_detail', order_id=order.id)


@login_required
def payment_cancel(request):
    """支払いキャンセル"""
    order_id = request.GET.get('order_id')
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # 注文をキャンセル
    order.status = 'cancelled'
    order.save()
    
    messages.warning(request, 'お支払いがキャンセルされました')
    return redirect('shop:cart')


@csrf_exempt
def stripe_webhook(request):
    """Stripeからのwebhook"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)
    
    # イベント処理
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        order_id = session['metadata'].get('order_id')
        
        if order_id:
            order = Order.objects.get(id=order_id)
            order.status = 'paid'
            order.stripe_payment_intent_id = session.get('payment_intent')
            order.save()
            
            # 在庫を減らす
            for item in order.items.all():
                product = item.product
                product.stock -= item.quantity
                product.save()
    
    return HttpResponse(status=200)


@login_required
def order_list(request):
    """注文履歴"""
    orders = Order.objects.filter(user=request.user).prefetch_related('items__product__tea')
    
    context = {
        'orders': orders,
    }
    return render(request, 'shop/order_list.html', context)


@login_required
def order_detail(request, order_id):
    """注文詳細"""
    order = get_object_or_404(
        Order, 
        id=order_id, 
        user=request.user
    )
    
    context = {
        'order': order,
    }
    return render(request, 'shop/order_detail.html', context)
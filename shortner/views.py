from django.shortcuts import render, redirect
from django.http import JsonResponse, Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone

from .models import Url
from captcha.models import CaptchaStore
from captcha.helpers import captcha_image_url  # Import this helper

import uuid
import qrcode
import io
# import base64 # Not strictly needed in create() if not sending QR as base64
from datetime import datetime


def index(request):
    """Main page view with URL shortener form and recent URLs"""
    urls = Url.objects.all().order_by('-created_at')[:10]
    # Initial CAPTCHA details will be loaded by JavaScript's refreshCaptcha() on page load.
    context = {
        'urls': urls,
    }
    return render(request, 'index.html', context)


@csrf_exempt
def create_api(request):
    """API endpoint for creating shortened URLs via AJAX"""
    if request.method == 'POST':
        link = request.POST.get('link')
        custom_code = request.POST.get('custom_code', '').strip()
        captcha_key = request.POST.get('captcha_key')
        captcha_value = request.POST.get('captcha')

        if not link:
            return JsonResponse({'error': 'URL is required'}, status=400)

        if not captcha_key or not captcha_value:
            return JsonResponse({'error': 'CAPTCHA key and value are required.'}, status=400)

        # Validate CAPTCHA
        try:
            captcha_store = CaptchaStore.objects.get(hashkey=captcha_key)

            response_matches = captcha_store.response.lower() == captcha_value.lower()

            # Always delete the CAPTCHA attempt to prevent replay.
            # A new one will be fetched by the client if needed via refreshCaptcha().
            captcha_store.delete()

            if not response_matches:
                return JsonResponse({'error': 'Invalid CAPTCHA. Please try again.'}, status=400)

        except CaptchaStore.DoesNotExist:
            # Key not found, likely expired and auto-cleaned by django-simple-captcha, or invalid key sent.
            return JsonResponse({'error': 'CAPTCHA session expired or invalid. Please refresh and try again.'},
                                status=400)

        if not link.startswith(('http://', 'https://')):
            link = 'https://' + link

        # Check for existing URL only if no custom code is provided
        # If a custom code is provided, we try to create it or fail if it exists.
        if not custom_code:
            existing = Url.objects.filter(link=link).first()
            if existing:
                return JsonResponse({
                    'short_url': existing.uuid,
                    'click_count': existing.click_count,
                    'created_at': existing.created_at.strftime("%b %d, %Y")
                }, status=200)

        uid = custom_code if custom_code else str(uuid.uuid4())[:5]

        if Url.objects.filter(uuid=uid).exists():
            # This check is especially important for custom codes.
            # For auto-generated codes, collision is rare but possible.
            # A more robust system might retry generation for auto-codes if a collision occurs.
            return JsonResponse({'error': 'Custom code already taken or collision with auto-generated code!'},
                                status=400)

        new_url = Url(link=link, uuid=uid)
        new_url.save()

        return JsonResponse({
            'short_url': uid,
            'click_count': 0,  # New URL, so 0 clicks
            'created_at': new_url.created_at.strftime("%b %d, %Y")
        }, status=200)

    return JsonResponse({'error': 'Invalid request method. Only POST is allowed.'}, status=405)


def create(request):
    """Non-AJAX form submission view (fallback/alternative)"""
    # This view is not currently used by the main form in index.html,
    # which uses create_api via AJAX.
    # If used, it would need its own CAPTCHA rendering and validation logic.
    if request.method == 'POST':
        link = request.POST.get('link')
        custom_code = request.POST.get('custom_code', '').strip()

        # Note: CAPTCHA validation is missing here.
        # If this form were to be a non-JS fallback, it would need full CAPTCHA handling.

        if not link:
            return render(request, 'index.html', {'error_message': 'URL is required'})  # Use a consistent error var

        if not link.startswith(('http://', 'https://')):
            link = 'https://' + link

        # Simplified logic as per create_api (without CAPTCHA for now)
        if not custom_code:
            existing = Url.objects.filter(link=link).first()
            if existing:
                # For non-AJAX, you might redirect to a success page or display info differently
                return render(request, 'index.html',
                              {'short_url_display': existing.uuid, 'original_url_display': existing.link})

        uid = custom_code if custom_code else str(uuid.uuid4())[:5]

        if Url.objects.filter(uuid=uid).exists():
            return render(request, 'index.html', {'error_message': 'Custom code already taken!'})

        new_url = Url(link=link, uuid=uid)
        new_url.save()

        # For non-AJAX, you might redirect or show a success message with the link
        return render(request, 'index.html', {'short_url_display': new_url.uuid, 'original_url_display': new_url.link})

    return redirect('index')


def go(request, pk):
    """Redirect to original URL and increment click counter"""
    try:
        url_details = Url.objects.get(uuid=pk)
        url_details.click_count += 1
        url_details.last_clicked = timezone.now()
        url_details.save()
        return redirect(url_details.link)
    except Url.DoesNotExist:
        return render(request, '404.html', status=404)


def generate_qr(request, pk):
    """Generate QR code for a shortened URL"""
    try:
        url_details = Url.objects.get(uuid=pk)
        # Construct the full URL to be encoded in the QR code
        # request.scheme will be 'http' or 'https'
        # request.get_host() will be 'localhost:8000' or your domain
        full_url = f"{request.scheme}://{request.get_host()}/{url_details.uuid}"

        qr = qrcode.make(full_url)
        buf = io.BytesIO()
        qr.save(buf, format='PNG')
        buf.seek(0)

        response = HttpResponse(buf, content_type='image/png')
        # Cache for a short period or not at all if stats are critical
        response['Cache-Control'] = 'max-age=0, no-cache, no-store, must-revalidate'
        return response

    except Url.DoesNotExist:
        raise Http404("URL not found, cannot generate QR code.")


def captcha_refresh(request):
    """Generate a new CAPTCHA and return its key and image URL."""
    new_key = CaptchaStore.generate_key()
    # captcha_image_url helper generates the path like '/captcha/image/your_key/'
    image_src_url = captcha_image_url(new_key)
    return JsonResponse({'key': new_key, 'image_url': image_src_url})


def get_url_stats(request, pk):
    """Get statistics for a specific URL (can be used for AJAX updates if needed)"""
    try:
        url = Url.objects.get(uuid=pk)
        return JsonResponse({
            'original_url': url.link,
            'short_url': url.uuid,  # This is pk
            'click_count': url.click_count,
            'created_at': url.created_at.strftime("%b %d, %Y"),
            'last_clicked': url.last_clicked.strftime("%b %d, %Y %H:%M") if url.last_clicked else "Never"
        })
    except Url.DoesNotExist:
        return JsonResponse({'error': 'URL not found'}, status=404)


def custom_404(request, exception):
    """Custom 404 page handler"""
    return render(request, '404.html', status=404)
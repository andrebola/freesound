from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.core.paginator import Paginator, InvalidPage
from django.http import Http404, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from sounds.models import Sound
from django.utils import simplejson
from django.views.decorators.cache import cache_page
from django.contrib.auth.models import User


def generate_json(sound_queryset):
    sounds_data = []
    
    for sound in sound_queryset:
        sounds_data.append([sound.id, sound.geotag.lat, sound.geotag.lon])
    
    return HttpResponse(simplejson.dumps(sounds_data))

@cache_page(60 * 15)
def geotags_json(request, tag=None):
    if tag:
        sounds = Sound.objects.select_related('geotag').filter(tags__tag__name=tag).exclude(geotag=None)
    else:
        sounds = Sound.objects.select_related('geotag').all().exclude(geotag=None)
    
    return generate_json(sounds)


@cache_page(60 * 15)
def geotags_for_user_json(request, username):
    sounds = Sound.objects.select_related('user', 'geotag').filter(user__username__iexact=username).exclude(geotag=None)
    return generate_json(sounds)


def geotags(request, tag=None):
    google_api_key = settings.GOOGLE_API_KEY
    for_user = None
    return render_to_response('geotags/geotags.html', locals(), context_instance=RequestContext(request))


def for_user(request, username):
    try:
        for_user = User.objects.get(username__iexact=username)
    except User.DoesNotExist: #@UndefinedVariable
        raise Http404
    google_api_key = settings.GOOGLE_API_KEY
    tag = None
    return render_to_response('geotags/geotags.html', locals(), context_instance=RequestContext(request))


def infowindow(request, sound_id):
    try:
        sound = Sound.objects.select_related('user', 'geotag').get(id=sound_id)
    except Sound.DoesNotExist: #@UndefinedVariable
        raise Http404
    
    return render_to_response('geotags/infowindow.html', locals(), context_instance=RequestContext(request))
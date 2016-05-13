# -*- coding: utf-8 -*-

#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#

from sounds.models import Sound, Pack
from ratings.models import Rating
from comments.models import Comment
from bookmarks.models import BookmarkCategory, Bookmark
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.conf import settings
from rest_framework import serializers
from utils.tags import clean_and_split_tags
from utils.forms import filename_has_valid_extension
from utils.similarity_utilities import get_sounds_descriptors
from apiv2_utils import prepend_base


###################
# SOUND SERIALIZERS
###################

DEFAULT_FIELDS_IN_SOUND_LIST = 'id,name,tags,username,license'  # Separated by commas (None = all)
DEFAULT_FIELDS_IN_SOUND_DETAIL = None  # Separated by commas (None = all)
DEFAULT_FIELDS_IN_PACK_DETAIL = None  # Separated by commas (None = all)


class AbstractSoundSerializer(serializers.HyperlinkedModelSerializer):
    '''
    In this abstract class we define ALL possible fields that a sound object should serialize/deserialize.
    Inherited classes set the default fields that will be shown in each view, although those can be altered using
    the 'fields' request parameter.
    '''
    default_fields = None

    def __init__(self, *args, **kwargs):
        super(AbstractSoundSerializer, self).__init__(*args, **kwargs)
        requested_fields = self.context['request'].GET.get("fields", self.default_fields)
        if not requested_fields: # If parameter is in url but parameter is empty, set to default
            requested_fields = self.default_fields

        if requested_fields:
            allowed = set(requested_fields.split(","))
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)


    class Meta:
        model = Sound
        fields = ('id',
                  #'uri',
                  'url',
                  'name',
                  'tags',
                  'description',
                  'geotag',
                  'created',
                  'license',
                  'type',
                  'channels',
                  'filesize',
                  'bitrate',
                  'bitdepth',
                  'duration',
                  'samplerate',
                  #'user',
                  'username',
                  'pack',
                  'download',
                  'bookmark',
                  'previews',
                  'images',
                  'num_downloads',
                  'avg_rating',
                  'num_ratings',
                  'rate',
                  'comments',
                  'num_comments',
                  'comment',
                  'similar_sounds',
                  'analysis',
                  'analysis_frames',
                  'analysis_stats',
                  )


    #uri = serializers.SerializerMethodField()
    #def get_uri(self, obj):
    #    return prepend_base(reverse('apiv2-sound-instance', args=[obj.id]), request_is_secure=self.context['request'].is_secure())

    url = serializers.SerializerMethodField()
    def get_url(self, obj):
        return prepend_base(reverse('sound', args=[obj.user.username, obj.id]), request_is_secure=self.context['request'].is_secure())

    #user = serializers.SerializerMethodField()
    #def get_user(self, obj):
    #    return prepend_base(reverse('apiv2-user-instance', args=[obj.user.username]), request_is_secure=self.context['request'].is_secure())

    username = serializers.SerializerMethodField()
    def get_username(self, obj):
        try:
            return obj.username
        except AttributeError:
            return obj.user.username

    name = serializers.SerializerMethodField()
    def get_name(self, obj):
        return obj.original_filename

    tags = serializers.SerializerMethodField()
    def get_tags(self, obj):
        try:
            return obj.tag_array
        except AttributeError:
            return [tagged.tag.name for tagged in obj.tags.select_related("tag").all()]

    license = serializers.SerializerMethodField()
    def get_license(self, obj):
        try:
            return obj.license_deed_url
        except AttributeError:
            return obj.license.deed_url

    pack = serializers.SerializerMethodField()
    def get_pack(self, obj):
        try:
            if obj.pack_id:
                return prepend_base(reverse('apiv2-pack-instance', args=[obj.pack_id]), request_is_secure=self.context['request'].is_secure())
            else:
                return None
        except:
            return None

    previews = serializers.SerializerMethodField()
    def get_previews(self, obj):
        return {
                'preview-hq-mp3': prepend_base(obj.locations("preview.HQ.mp3.url"), request_is_secure=self.context['request'].is_secure()),
                'preview-hq-ogg': prepend_base(obj.locations("preview.HQ.ogg.url"), request_is_secure=self.context['request'].is_secure()),
                'preview-lq-mp3': prepend_base(obj.locations("preview.LQ.mp3.url"), request_is_secure=self.context['request'].is_secure()),
                'preview-lq-ogg': prepend_base(obj.locations("preview.LQ.ogg.url"), request_is_secure=self.context['request'].is_secure()),
        }

    images = serializers.SerializerMethodField()
    def get_images(self, obj):
        return {
                'waveform_m': prepend_base(obj.locations("display.wave.M.url"), request_is_secure=self.context['request'].is_secure()),
                'waveform_l': prepend_base(obj.locations("display.wave.L.url"), request_is_secure=self.context['request'].is_secure()),
                'spectral_m': prepend_base(obj.locations("display.spectral.M.url"), request_is_secure=self.context['request'].is_secure()),
                'spectral_l': prepend_base(obj.locations("display.spectral.L.url"), request_is_secure=self.context['request'].is_secure()),
        }

    analysis = serializers.SerializerMethodField()
    def get_analysis(self, obj):
        # Fake implementation. Method implemented in subclasses
        return None

    analysis_frames = serializers.SerializerMethodField()
    def get_analysis_frames(self, obj):
        return prepend_base(obj.locations('analysis.frames.url'), request_is_secure=self.context['request'].is_secure())

    analysis_stats = serializers.SerializerMethodField()
    def get_analysis_stats(self, obj):
        return prepend_base(reverse('apiv2-sound-analysis', args=[obj.id]), request_is_secure=self.context['request'].is_secure())

    similar_sounds = serializers.SerializerMethodField()
    def get_similar_sounds(self, obj):
        return prepend_base(reverse('apiv2-similarity-sound', args=[obj.id]), request_is_secure=self.context['request'].is_secure())

    download = serializers.SerializerMethodField()
    def get_download(self, obj):
        return prepend_base(reverse('apiv2-sound-download', args=[obj.id]), request_is_secure=self.context['request'].is_secure())

    rate = serializers.SerializerMethodField()
    def get_rate(self, obj):
        return prepend_base(reverse('apiv2-user-create-rating', args=[obj.id]), request_is_secure=self.context['request'].is_secure())

    bookmark = serializers.SerializerMethodField()
    def get_bookmark(self, obj):
        return prepend_base(reverse('apiv2-user-create-bookmark', args=[obj.id]), request_is_secure=self.context['request'].is_secure())

    comment = serializers.SerializerMethodField()
    def get_comment(self, obj):
        return prepend_base(reverse('apiv2-user-create-comment', args=[obj.id]), request_is_secure=self.context['request'].is_secure())

    ratings = serializers.SerializerMethodField()
    def get_ratings(self, obj):
        return prepend_base(reverse('apiv2-sound-ratings', args=[obj.id]), request_is_secure=self.context['request'].is_secure())

    avg_rating = serializers.SerializerMethodField()
    def get_avg_rating(self, obj):
        return obj.avg_rating/2

    comments = serializers.SerializerMethodField()
    def get_comments(self, obj):
        return prepend_base(reverse('apiv2-sound-comments', args=[obj.id]), request_is_secure=self.context['request'].is_secure())

    geotag = serializers.SerializerMethodField()
    def get_geotag(self, obj):
        if obj.geotag:
            return str(obj.geotag.lat) + " " + str(obj.geotag.lon)
        else:
            return None


class SoundListSerializer(AbstractSoundSerializer):

    def __init__(self, *args, **kwargs):
        self.default_fields = DEFAULT_FIELDS_IN_SOUND_LIST
        super(SoundListSerializer, self).__init__(*args, **kwargs)

    def get_analysis(self, obj):
        # Get descriptors from the view class (should have been requested before the serializer is invoked)
        try:
            return self.context['view'].sound_analysis_data[str(obj.id)]
        except Exception, e:
            return None


class SoundSerializer(AbstractSoundSerializer):

    def __init__(self, *args, **kwargs):
        self.default_fields = DEFAULT_FIELDS_IN_SOUND_DETAIL
        super(SoundSerializer, self).__init__(*args, **kwargs)

    def get_analysis(self, obj):
        # Get the sound descriptors from gaia
        try:
            descriptors = self.context['request'].GET.get('descriptors', [])
            if descriptors:
                return get_sounds_descriptors([obj.id],
                                              descriptors.split(','),
                                              self.context['request'].GET.get('normalized', '0') == '1',
                                              only_leaf_descriptors=True)[str(obj.id)]
            else:
                return 'No descriptors specified. You should indicate which descriptors you want with the \'descriptors\' request parameter.'
        except Exception, e:
            return None


##################
# USER SERIALIZERS
##################


class UserSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = User
        fields = (#'uri',
                  'url',
                  'username',
                  'about',
                  'home_page',
                  'avatar',
                  'date_joined',
                  'num_sounds',
                  'sounds',
                  'num_packs',
                  'packs',
                  'num_posts',
                  'num_comments',
                  'bookmark_categories',
                  )

    url = serializers.SerializerMethodField()
    def get_url(self, obj):
        return prepend_base(reverse('account', args=[obj.username]), request_is_secure=self.context['request'].is_secure())

    #uri = serializers.SerializerMethodField('get_uri')
    #def get_uri(self, obj):
    #    return prepend_base(reverse('apiv2-user-instance', args=[obj.username]), request_is_secure=self.context['request'].is_secure())

    sounds = serializers.SerializerMethodField()
    def get_sounds(self, obj):
        return prepend_base(reverse('apiv2-user-sound-list', args=[obj.username]), request_is_secure=self.context['request'].is_secure())

    packs = serializers.SerializerMethodField()
    def get_packs(self, obj):
        return prepend_base(reverse('apiv2-user-packs', args=[obj.username]), request_is_secure=self.context['request'].is_secure())

    bookmark_categories = serializers.SerializerMethodField()
    def get_bookmark_categories(self, obj):
        return prepend_base(reverse('apiv2-user-bookmark-categories', args=[obj.username]), request_is_secure=self.context['request'].is_secure())

    avatar = serializers.SerializerMethodField()
    def get_avatar(self, obj):
        return {
                'small': prepend_base(obj.profile.locations()['avatar']['S']['url'], request_is_secure=self.context['request'].is_secure()),
                'medium': prepend_base(obj.profile.locations()['avatar']['M']['url'], request_is_secure=self.context['request'].is_secure()),
                'large': prepend_base(obj.profile.locations()['avatar']['L']['url'], request_is_secure=self.context['request'].is_secure()),
        }

    about = serializers.SerializerMethodField()
    def get_about(self, obj):
        return obj.profile.about or ""

    home_page = serializers.SerializerMethodField()
    def get_home_page(self, obj):
        return obj.profile.home_page or ""

    num_sounds = serializers.SerializerMethodField()
    def get_num_sounds(self, obj):
        return obj.sounds.filter(moderation_state="OK", processing_state="OK").count()

    num_packs = serializers.SerializerMethodField()
    def get_num_packs(self, obj):
        return obj.pack_set.all().count()

    num_posts = serializers.SerializerMethodField()
    def get_num_posts(self, obj):
        return obj.profile.num_posts

    num_comments = serializers.SerializerMethodField()
    def get_num_comments(self, obj):
        return obj.comment_set.all().count()


##################
# PACK SERIALIZERS
##################


class PackSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Pack
        fields = ('id',
                  #'uri',
                  'url',
                  'description',
                  'created',
                  'name',
                  #'user',
                  'username',
                  'num_sounds',
                  'sounds',
                  'num_downloads')

    url = serializers.SerializerMethodField()
    def get_url(self, obj):
        return prepend_base(reverse('pack', args=[obj.user.username, obj.id]), request_is_secure=self.context['request'].is_secure())

    #uri = serializers.SerializerMethodField('get_uri')
    #def get_uri(self, obj):
    #    return prepend_base(reverse('apiv2-pack-instance', args=[obj.id]), request_is_secure=self.context['request'].is_secure())

    sounds = serializers.SerializerMethodField()
    def get_sounds(self, obj):
        return prepend_base(reverse('apiv2-pack-sound-list', args=[obj.id]), request_is_secure=self.context['request'].is_secure())

    #user = serializers.SerializerMethodField('get_user')
    #def get_user(self, obj):
    #    return prepend_base(reverse('apiv2-user-instance', args=[obj.user.username]), request_is_secure=self.context['request'].is_secure())

    username = serializers.SerializerMethodField()
    def get_username(self, obj):
        return obj.user.username

    description = serializers.SerializerMethodField()
    def get_description(self, obj):
        return obj.description or ""

##################
# BOOKMARK SERIALIZERS
##################


class BookmarkCategorySerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = BookmarkCategory
        fields = ('url',
                  'name',
                  'num_sounds',
                  'sounds')

    url = serializers.SerializerMethodField()
    def get_url(self, obj):
        if obj.id != 0:
            return prepend_base(reverse('bookmarks-for-user-for-category', args=[obj.user.username, obj.id]), request_is_secure=self.context['request'].is_secure())
        else:
            return prepend_base(reverse('bookmarks-for-user', args=[obj.user.username]), request_is_secure=self.context['request'].is_secure())

    num_sounds = serializers.SerializerMethodField()
    def get_num_sounds(self, obj):
        if obj.id != 0:  # Category is not 'uncategorized'
            return obj.bookmarks.filter(sound__processing_state="OK", sound__moderation_state="OK").count()
        else:
            return Bookmark.objects.select_related("sound").filter(user__username=obj.user.username, category=None).count()

    sounds = serializers.SerializerMethodField()
    def get_sounds(self, obj):
        return prepend_base(reverse('apiv2-user-bookmark-category-sounds', args=[obj.user.username, obj.id]), request_is_secure=self.context['request'].is_secure())


class CreateBookmarkSerializer(serializers.Serializer):
    category = serializers.CharField(max_length=128, required=False, help_text='Not required. Name you want to give to the category under which the bookmark will be classified (leave empty for no category).')
    name = serializers.CharField(max_length=128, required=False, help_text='Not required. Name you want to give to the bookmark (if empty, sound name will be used).')

    def validate_category(self, value):
        if value.isspace():
            value = None
        return value

    def validate_name(self, value):
        if value.isspace():
            value = None
        return value


####################
# RATING SERIALIZERS
####################

class SoundRatingsSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Rating
        fields = (#'user',
                  'username',
                  'rating',
                  'created')

    #user = serializers.SerializerMethodField()
    #def get_user(self, obj):
    #    return prepend_base(reverse('apiv2-user-instance', args=[obj.user.username]), request_is_secure=self.context['request'].is_secure())

    username = serializers.SerializerMethodField()
    def get_username(self, obj):
        return obj.user.username

    rating = serializers.SerializerMethodField()
    def get_rating(self, obj):
        if (obj.rating % 2 == 1):
            return float(obj.rating)/2
        else:
            return obj.rating/2


class CreateRatingSerializer(serializers.Serializer):
    rating = serializers.IntegerField(required=True, help_text='Required. Chose an integer rating between 0 and 5 (both included).')

    def validate_rating(self, value):
        if (value not in [0, 1, 2, 3, 4, 5]):
            raise serializers.ValidationError('You have to introduce an integer value between 0 and 5 (both included).')
        return value

####################
# COMMENTS SERIALIZERS
####################

class SoundCommentsSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Comment
        fields = (#'user',
                  'username',
                  'comment',
                  'created')

    #user = serializers.SerializerMethodField()
    #def get_user(self, obj):
    #    return prepend_base(reverse('apiv2-user-instance', args=[obj.user.username]), request_is_secure=self.context['request'].is_secure())

    username = serializers.SerializerMethodField()
    def get_username(self, obj):
        return obj.user.username


class CreateCommentSerializer(serializers.Serializer):
    comment = serializers.CharField(required=True, help_text='Required. String comment.')

    def validate_comment(self, value):
        if value.isspace():
            raise serializers.ValidationError('This field is required.')
        return value


####################
# UPLOAD SERIALIZERS
####################

def validate_license(value):
    if value not in [key for key, name in LICENSE_CHOICES]:
        raise serializers.ValidationError('Invalid License, must be either \'Attribution\', \'Attribution Noncommercial\' or \'Creative Commons 0\'.')
    return value


def validate_name(value):
    if value.isspace():
        value = None
    return value


def validate_tags(value):
    tags = clean_and_split_tags(value)
    if len(tags) < 3:
        raise serializers.ValidationError('You should add at least 3 tags...')
    elif len(tags) > 30:
        raise serializers.ValidationError('There can be maximum 30 tags, please select the most relevant ones!')
    return value


def validate_description(value):
    if not value or value.isspace():
        raise serializers.ValidationError('This field is required.')
    return value


def validate_pack(value):
    if value.isspace():
        value = None
    return value


def validate_geotag(value):
    if value:
        fails = False
        try:
            data = value.split(',')
        except:
            fails = True
        if len(data) != 3:
            fails = True
        try:
            float(data[0])
            float(data[1])
            int(data[2])
        except:
            fails = True
        if fails:
            raise serializers.ValidationError('Geotag should have the format \'float,float,integer\' (for latitude, longitude and zoom respectively).')
        else:
            # Check that ranges are corrent
            if float(data[0]) > 90 or float(data[0]) < -90:
                raise serializers.ValidationError('Latitude must be in the range [-90,90].')
            if float(data[1]) > 180 or float(data[0]) < -180:
                raise serializers.ValidationError('Longitude must be in the range [-180,180].')
            if int(data[2]) < 11:
                raise serializers.ValidationError('Zoom must be at least 11.')
    return value


LICENSE_CHOICES = (
        ('Attribution', 'Attribution'),
        ('Attribution Noncommercial', 'Attribution Noncommercial'),
        ('Creative Commons 0', 'Creative Commons 0'),)


class SoundDescriptionSerializer(serializers.Serializer):
    upload_filename = serializers.CharField(max_length=512, help_text='Must match a filename from \'Pending Uploads\' resource.')
    name = serializers.CharField(max_length=512, required=False, help_text='Not required. Name you want to give to the sound (by default it will be the original filename).')
    tags = serializers.CharField(max_length=512, help_text='Separate tags with spaces. Join multi-word tags with dashes.')
    description = serializers.CharField(help_text='Textual description of the sound.')
    license = serializers.ChoiceField(choices=LICENSE_CHOICES, help_text='License for the sound. Must be either \'Attribution\', \'Attribution Noncommercial\' or \'Creative Commons 0\'.')
    pack = serializers.CharField(help_text='Not required. Pack name (if there is no such pack with that name, a new one will be created).', required=False)
    geotag = serializers.CharField(max_length=100, help_text='Not required. Latitude, longitude and zoom values in the form lat,lon,zoom (ex: \'2.145677,3.22345,14\').', required=False)

    def validate_upload_filename(self, value):
        if 'not_yet_described_audio_files' in self.context:
            if value not in self.context['not_yet_described_audio_files']:
                raise serializers.ValidationError('Upload filename (%s) must match with a filename from \'Pending Uploads\' resource.' % value)
        return value

    def validate_geotag(self, value):
        return validate_geotag(value)

    def validate_tags(self, value):
        return validate_tags(value)

    def validate_name(self, value):
        return validate_name(value)

    def validate_description(self, value):
        return validate_description(value)

    def validate_pack(self, value):
        return validate_pack(value)


class EditSoundDescriptionSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=512, required=False, help_text='Not required. New name you want to give to the sound.')
    tags = serializers.CharField(max_length=512, required=False, help_text='Not required. Tags that should be assigned to the sound (note that existing ones will be deleted). Separate tags with spaces. Join multi-word tags with dashes.')
    description = serializers.CharField(required=False, help_text='Not required. New textual description for the sound.')
    license = serializers.ChoiceField(required=False, allow_blank=True, choices=LICENSE_CHOICES, help_text='Not required. New license for the sound. Must be either \'Attribution\', \'Attribution Noncommercial\' or \'Creative Commons 0\'.')
    pack = serializers.CharField(required=False, help_text='Not required. New pack name for the sound (if there is no such pack with that name, a new one will be created).')
    geotag = serializers.CharField(required=False, max_length=100, help_text='Not required. New geotag for the sound. Latitude, longitude and zoom values in the form lat,lon,zoom (ex: \'2.145677,3.22345,14\').')

    def validate_geotag(self, value):
        return validate_geotag(value)

    def validate_tags(self, value):
        return validate_tags(value)

    def validate_name(self, value):
        return validate_name(value)

    def validate_description(self, value):
        return validate_description(value)

    def validate_pack(self, value):
        return validate_pack(value)


class UploadAndDescribeAudioFileSerializer(serializers.Serializer):
    audiofile = serializers.FileField(max_length=100, allow_empty_file=False, help_text='Required. Must be in .wav, .aif, .flac, .ogg or .mp3 format.')
    name = serializers.CharField(max_length=512, required=False, help_text='Not required. Name you want to give to the sound (by default it will be the original filename).')
    tags = serializers.CharField(max_length=512, required=False, help_text='Only required if providing file description. Separate tags with spaces. Join multi-word tags with dashes.')
    description = serializers.CharField(required=False, help_text='Only required if providing file description. Textual description of the sound.')
    license = serializers.ChoiceField(required=False, allow_blank=True, choices=LICENSE_CHOICES, help_text='Only required if providing file description. License for the sound. Must be either \'Attribution\', \'Attribution Noncommercial\' or \'Creative Commons 0\'.')
    pack = serializers.CharField(help_text='Not required. Pack name (if there is no such pack with that name, a new one will be created).', required=False)
    geotag = serializers.CharField(max_length=100, help_text='Not required. Latitude, longitude and zoom values in the form lat,lon,zoom (ex: \'2.145677,3.22345,14\').', required=False)

    def is_providing_description(self, attrs):
        if attrs['name'] or attrs['license'] or attrs['tags'] \
          or attrs['geotag'] or attrs['pack'] or attrs['description']:
            return True
        return False

    def validate_audiofile(self, value):
        if not filename_has_valid_extension(str(value)):
            raise serializers.ValidationError('Uploaded file format not supported or not an audio file.')
        return value

    def validate(self, data):
        is_providing_description = self.is_providing_description(self.initial_data)
        if not is_providing_description:
            #  No need to validate individual fields because no description is provided
            return data

        # Validate description fileds
        errors = dict()
        try:
            data['description'] = validate_description(self.initial_data['description'])
        except serializers.ValidationError as e:
            errors['description'] = e.detail
        try:
            data['name'] = validate_name(self.initial_data['name'])
        except serializers.ValidationError as e:
            errors['name'] = e.detail
        try:
            data['tags'] = validate_tags(self.initial_data['tags'])
        except serializers.ValidationError as e:
            errors['tags'] = e.detail
        try:
            data['geotag'] = validate_geotag(self.initial_data['geotag'])
        except serializers.ValidationError as e:
            errors['geotag'] = e.detail
        try:
            data['pack'] = validate_pack(self.initial_data['pack'])
        except serializers.ValidationError as e:
            errors['pack'] = e.detail
        try:
            data['license'] = validate_license(self.initial_data['license'])
        except serializers.ValidationError as e:
            errors['license'] = e.detail
        if len(errors):
            raise serializers.ValidationError(errors)
        return data

########################
# SIMILARITY SERIALIZERS
########################

ALLOWED_ANALYSIS_EXTENSIONS = ['json']

class SimilarityFileSerializer(serializers.Serializer):
    analysis_file = serializers.FileField(max_length=100, allow_empty_file=False, help_text='Analysis file created with the latest freesound extractor. Must be in .json format.')

    def validate_analysis_file(self, value):
        try:
            extension = value.name.split('.')[-1]
        except:
            extension = None

        if extension not in ALLOWED_ANALYSIS_EXTENSIONS or not extension:
            raise serializers.ValidationError('Uploaded analysis file format not supported, must be .json.')

        return value

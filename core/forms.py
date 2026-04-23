from django import forms
from django.db import transaction
from django.contrib.auth.models import User
from .models import ContactMessage, EventRegistration
from accounts.models import Zone, ChurchBranch, UserProfile, ChurchLeader, DeaconGroup, FamilyMember
from .models import (
    Ministry, Event, EventCategory, OfferingRecord, FundraisingContribution,
    ChurchAsset, ChurchAssetCategory, OfferingCategory, FundraisingCampaign,
)

class ContactForm(forms.ModelForm):
    """Contact form"""
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Email'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Phone Number'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Subject'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Your Message',
                'rows': 5
            }),
        }

class EventRegistrationForm(forms.ModelForm):
    """Event registration form"""
    class Meta:
        model = EventRegistration
        fields = ['full_name', 'email', 'phone']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email Address'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone Number'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Pre-fill with user data if available
        if self.user and self.user.is_authenticated:
            self.fields['full_name'].initial = self.user.get_full_name()
            self.fields['email'].initial = self.user.email
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if self.event and EventRegistration.objects.filter(event=self.event, email=email).exists():
            raise forms.ValidationError("This email is already registered for this event.")
        return email


class StyledFormMixin:
    def apply_bootstrap(self):
        for field in self.fields.values():
            css_class = 'form-control'
            if isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                css_class = 'form-select'
            elif isinstance(field.widget, forms.CheckboxInput):
                css_class = 'form-check-input'
            existing = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f'{existing} {css_class}'.strip()


class OfficerMemberCreateForm(forms.Form, StyledFormMixin):
    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput, required=False)
    phone = forms.CharField(max_length=20, required=False)
    church_branch = forms.CharField(max_length=100, required=False)
    zone = forms.ModelChoiceField(queryset=Zone.objects.order_by('name'), required=False)
    deacon_group = forms.ModelChoiceField(queryset=DeaconGroup.objects.filter(is_active=True).order_by('zone__name', 'name'), required=False)
    ministry_role = forms.ModelChoiceField(queryset=Ministry.objects.filter(status='active').order_by('name'), required=False)
    tithe_card_number = forms.CharField(max_length=50, required=False)
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    is_staff = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        self.user_instance = kwargs.pop('user_instance', None)
        self.profile_instance = kwargs.pop('profile_instance', None)
        self.allow_staff_toggle = kwargs.pop('allow_staff_toggle', True)
        super().__init__(*args, **kwargs)
        if self.user_instance:
            self.fields['username'].initial = self.user_instance.username
            self.fields['first_name'].initial = self.user_instance.first_name
            self.fields['last_name'].initial = self.user_instance.last_name
            self.fields['email'].initial = self.user_instance.email
            self.fields['is_staff'].initial = self.user_instance.is_staff
            self.fields['password'].help_text = 'Leave blank to keep current password.'
        if self.profile_instance:
            self.fields['phone'].initial = self.profile_instance.phone
            self.fields['church_branch'].initial = self.profile_instance.church_branch
            self.fields['zone'].initial = self.profile_instance.zone
            self.fields['deacon_group'].initial = self.profile_instance.deacon_group
            self.fields['ministry_role'].initial = self.profile_instance.ministry_role
            self.fields['tithe_card_number'].initial = self.profile_instance.tithe_card_number
            self.fields['date_of_birth'].initial = self.profile_instance.date_of_birth
        if not self.allow_staff_toggle:
            self.fields['is_staff'].disabled = True
            self.fields['is_staff'].help_text = 'Role assignment for staff accounts is handled by pastor/secretary.'
        self.apply_bootstrap()

    def clean_username(self):
        username = self.cleaned_data['username']
        queryset = User.objects.filter(username__iexact=username)
        if self.user_instance:
            queryset = queryset.exclude(pk=self.user_instance.pk)
        if queryset.exists():
            raise forms.ValidationError('Username already exists.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        queryset = User.objects.filter(email__iexact=email)
        if self.user_instance:
            queryset = queryset.exclude(pk=self.user_instance.pk)
        if queryset.exists():
            raise forms.ValidationError('Email already exists.')
        return email

    def clean_tithe_card_number(self):
        tithe_card_number = (self.cleaned_data.get('tithe_card_number') or '').strip()
        queryset = UserProfile.objects.exclude(tithe_card_number__isnull=True).exclude(tithe_card_number='')
        if self.profile_instance:
            queryset = queryset.exclude(pk=self.profile_instance.pk)
        if tithe_card_number and queryset.filter(tithe_card_number__iexact=tithe_card_number).exists():
            raise forms.ValidationError('Tithe card number already exists.')
        return tithe_card_number or None

    def clean(self):
        cleaned_data = super().clean()
        zone = cleaned_data.get('zone')
        deacon_group = cleaned_data.get('deacon_group')
        if deacon_group and zone and deacon_group.zone_id != zone.id:
            self.add_error('deacon_group', 'Selected deacon group does not belong to the chosen zone.')
        if deacon_group and not zone:
            cleaned_data['zone'] = deacon_group.zone
        return cleaned_data

    @transaction.atomic
    def save(self):
        if self.user_instance:
            user = self.user_instance
            user.username = self.cleaned_data['username']
            user.email = self.cleaned_data['email']
            user.first_name = self.cleaned_data.get('first_name', '')
            user.last_name = self.cleaned_data.get('last_name', '')
            if self.allow_staff_toggle:
                user.is_staff = self.cleaned_data.get('is_staff', False)
            if self.cleaned_data.get('password'):
                user.set_password(self.cleaned_data['password'])
            user.save()
            profile = self.profile_instance or UserProfile.objects.get(user=user)
            profile.phone = self.cleaned_data.get('phone', '')
            profile.church_branch = self.cleaned_data.get('church_branch', '')
            profile.zone = self.cleaned_data.get('zone')
            profile.deacon_group = self.cleaned_data.get('deacon_group')
            profile.ministry_role = self.cleaned_data.get('ministry_role')
            profile.tithe_card_number = self.cleaned_data.get('tithe_card_number')
            profile.date_of_birth = self.cleaned_data.get('date_of_birth')
            profile.save()
        else:
            user = User.objects.create_user(
                username=self.cleaned_data['username'],
                email=self.cleaned_data['email'],
                password=self.cleaned_data['password'],
                first_name=self.cleaned_data.get('first_name', ''),
                last_name=self.cleaned_data.get('last_name', ''),
                is_staff=self.cleaned_data.get('is_staff', False) if self.allow_staff_toggle else False,
            )
            UserProfile.objects.create(
                user=user,
                phone=self.cleaned_data.get('phone', ''),
                church_branch=self.cleaned_data.get('church_branch', ''),
                zone=self.cleaned_data.get('zone'),
                deacon_group=self.cleaned_data.get('deacon_group'),
                ministry_role=self.cleaned_data.get('ministry_role'),
                tithe_card_number=self.cleaned_data.get('tithe_card_number'),
                date_of_birth=self.cleaned_data.get('date_of_birth'),
            )
        return user

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not self.user_instance and not password:
            raise forms.ValidationError('Password is required for a new member.')
        return password


class ContactMessageStatusForm(forms.ModelForm, StyledFormMixin):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'subject', 'message', 'status']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()


class ZoneForm(forms.ModelForm, StyledFormMixin):
    class Meta:
        model = Zone
        fields = ['name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()


class ChurchBranchForm(forms.ModelForm, StyledFormMixin):
    class Meta:
        model = ChurchBranch
        fields = ['name', 'zone']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()


class ChurchLeaderForm(forms.ModelForm, StyledFormMixin):
    class Meta:
        model = ChurchLeader
        fields = ['full_name', 'title', 'level', 'photo', 'vision_message', 'biography', 'is_active', 'order']
        widgets = {
            'vision_message': forms.Textarea(attrs={'rows': 3}),
            'biography': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()


class MinistryForm(forms.ModelForm, StyledFormMixin):
    class Meta:
        model = Ministry
        fields = [
            'name', 'tagline', 'description', 'leader', 'contact_email', 'contact_phone',
            'logo', 'banner_image', 'meeting_days', 'meeting_time', 'meeting_location',
            'status', 'is_featured', 'order'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['leader'].queryset = User.objects.filter(is_active=True).order_by('first_name', 'username')
        self.apply_bootstrap()


class EventForm(forms.ModelForm, StyledFormMixin):
    class Meta:
        model = Event
        fields = [
            'title', 'description', 'short_description', 'event_type', 'category',
            'start_date', 'start_time', 'end_date', 'end_time', 'is_recurring',
            'location', 'location_details', 'online_link', 'featured_image',
            'requires_registration', 'max_attendees', 'registration_deadline',
            'status', 'is_featured'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'short_description': forms.Textarea(attrs={'rows': 3}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'registration_deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'location_details': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = EventCategory.objects.order_by('name')
        self.apply_bootstrap()


class OfferingRecordForm(forms.ModelForm, StyledFormMixin):
    class Meta:
        model = OfferingRecord
        fields = ['category', 'zone', 'deacon_group', 'amount', 'week_label', 'month', 'year', 'service_date', 'notes']
        widgets = {
            'service_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = OfferingCategory.objects.filter(is_active=True).order_by('name')
        self.fields['zone'].queryset = Zone.objects.order_by('name')
        self.fields['deacon_group'].queryset = DeaconGroup.objects.filter(is_active=True).order_by('zone__name', 'name')
        self.apply_bootstrap()


class FundraisingContributionForm(forms.ModelForm, StyledFormMixin):
    class Meta:
        model = FundraisingContribution
        fields = ['campaign', 'contributor', 'zone', 'amount', 'contribution_date', 'week_label', 'notes']
        widgets = {
            'contribution_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['campaign'].queryset = FundraisingCampaign.objects.filter(is_active=True).order_by('-start_date', 'name')
        self.fields['contributor'].queryset = User.objects.filter(is_active=True).order_by('first_name', 'username')
        self.fields['zone'].queryset = Zone.objects.order_by('name')
        self.apply_bootstrap()


class ChurchAssetForm(forms.ModelForm, StyledFormMixin):
    class Meta:
        model = ChurchAsset
        fields = ['name', 'category', 'serial_number', 'quantity', 'condition', 'location', 'purchased_on', 'estimated_value', 'status', 'notes']
        widgets = {
            'purchased_on': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = ChurchAssetCategory.objects.order_by('name')
        self.apply_bootstrap()


class FamilyMemberForm(forms.ModelForm, StyledFormMixin):
    class Meta:
        model = FamilyMember
        fields = ['full_name', 'relationship', 'gender', 'date_of_birth', 'phone', 'is_member_account', 'notes']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()


class UserRoleAssignmentForm(forms.ModelForm, StyledFormMixin):
    is_staff = forms.BooleanField(required=False)

    class Meta:
        model = UserProfile
        fields = ['role', 'zone', 'deacon_group', 'church_branch', 'ministry_role', 'tithe_card_number']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['zone'].queryset = Zone.objects.order_by('name')
        self.fields['deacon_group'].queryset = DeaconGroup.objects.filter(is_active=True).order_by('zone__name', 'name')
        self.fields['ministry_role'].queryset = Ministry.objects.filter(status='active').order_by('name')
        if self.instance and self.instance.user_id:
            self.fields['is_staff'].initial = self.instance.user.is_staff
        self.apply_bootstrap()

    def clean(self):
        cleaned_data = super().clean()
        zone = cleaned_data.get('zone')
        deacon_group = cleaned_data.get('deacon_group')
        role = cleaned_data.get('role')
        if deacon_group and zone and deacon_group.zone_id != zone.id:
            self.add_error('deacon_group', 'Selected deacon group does not belong to the chosen zone.')
        if deacon_group and not zone:
            cleaned_data['zone'] = deacon_group.zone
        if role == 'deacon_leader' and not deacon_group:
            self.add_error('deacon_group', 'Deacon leader must have a deacon group assignment.')
        if role == 'zone_leader' and not cleaned_data.get('zone'):
            self.add_error('zone', 'Zone leader must have a zone assignment.')
        return cleaned_data

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.save()
            user = profile.user
            user.is_staff = self.cleaned_data.get('is_staff', False)
            user.save(update_fields=['is_staff'])
        return profile


class ZoneLeadershipForm(forms.Form, StyledFormMixin):
    user = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True).order_by('first_name', 'username'))
    zone = forms.ModelChoiceField(queryset=Zone.objects.order_by('name'))
    role = forms.ChoiceField(choices=[('zone_leader', 'Zone Leader'), ('assistant_zone_leader', 'Assistant Zone Leader')])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()


class DeaconGroupForm(forms.ModelForm, StyledFormMixin):
    class Meta:
        model = DeaconGroup
        fields = ['name', 'zone', 'leader', 'description', 'is_active']
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['zone'].queryset = Zone.objects.order_by('name')
        self.fields['leader'].queryset = User.objects.filter(is_active=True).order_by('first_name', 'username')
        self.apply_bootstrap()

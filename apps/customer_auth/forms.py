from django import forms
import re


class CustomerLoginForm(forms.Form):
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "e.g. +91 9876543210 or 9876543210",
                "required": True,
                "type": "tel",
            }
        ),
        label="Phone Number",
    )
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "form-input",
                "placeholder": "your.email@example.com",
                "required": True,
            }
        ),
        label="Email Address",
    )

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        # Remove common separators (spaces, dashes, parens) for consistency
        cleaned = re.sub(r"[\s\-\(\)]", "", phone)
        if not cleaned or len(cleaned) < 7:
            raise forms.ValidationError("Please enter a valid phone number.")
        return cleaned

    def clean_email(self):
        return self.cleaned_data.get("email", "").strip().lower()


class OTPVerifyForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(
            attrs={
                "class": "form-input text-center text-xl tracking-wider",
                "placeholder": "123456",
                "required": True,
                "maxlength": "6",
                "pattern": "[0-9]{6}",
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "style": "font-family: monospace; letter-spacing: 0.4em; font-size: 1.5rem; text-align: center;",
            }
        ),
        label="6-Digit Verification Code",
    )

    def clean_otp(self):
        otp = self.cleaned_data.get("otp", "").strip()
        if not otp.isdigit() or len(otp) != 6:
            raise forms.ValidationError("OTP must be a 6-digit number.")
        return otp

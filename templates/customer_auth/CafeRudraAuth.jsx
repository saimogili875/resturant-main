import React, { useState, useEffect } from 'react';
import { 
  Utensils, 
  Mail, 
  Phone, 
  ArrowRight, 
  CheckCircle2, 
  AlertCircle, 
  Sparkles, 
  ShieldCheck,
  RefreshCw,
  ChevronLeft
} from 'lucide-react';

export default function CafeRudraAuth() {
  const [activeTab, setActiveTab] = useState('signin'); // 'signin' | 'signup'
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [step, setStep] = useState('credentials'); // 'credentials' | 'otp'
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [timer, setTimer] = useState(45);
  const [canResend, setCanResend] = useState(false);

  // Countdown timer for OTP resend
  useEffect(() => {
    let interval = null;
    if (step === 'otp' && timer > 0) {
      interval = setInterval(() => setTimer((t) => t - 1), 1000);
    } else if (timer === 0) {
      setCanResend(true);
    }
    return () => clearInterval(interval);
  }, [step, timer]);

  // Tab Switching Handler
  const handleTabSwitch = (newTab) => {
    setActiveTab(newTab);
    setError(null);
    setSuccess(null);
    setStep('credentials');
  };

  // Credentials Submission Handler
  const handleSubmit = (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    // Validation Rules
    if (!email || !email.includes('@')) {
      setError({ message: 'Please enter a valid email address.' });
      return;
    }

    if (activeTab === 'signup' && (!phone || phone.replace(/\D/g, '').length < 10)) {
      setError({ message: 'Please enter a valid 10-digit phone number.' });
      return;
    }

    setIsLoading(true);

    // Simulated API Call
    setTimeout(() => {
      setIsLoading(false);

      // Smart Error Handling Simulation
      const lowerEmail = email.toLowerCase().strip ? email.toLowerCase().strip() : email.toLowerCase();
      
      // Simulate "Existing email entered in Create Account mode"
      if (activeTab === 'signup' && (lowerEmail === 'user@caferudra.com' || lowerEmail === 'existing@example.com')) {
        setError({
          message: 'An account with this email already exists.',
          actionText: 'Sign In Instead',
          targetTab: 'signin',
        });
        return;
      }

      // Simulate "Unregistered email entered in Sign In mode"
      if (activeTab === 'signin' && (lowerEmail === 'new@example.com' || lowerEmail === 'unregistered@caferudra.com')) {
        setError({
          message: "No registered account found with this email.",
          actionText: "Create an Account",
          targetTab: "signup",
        });
        return;
      }

      // Success -> Proceed to OTP Step
      setStep('otp');
      setTimer(45);
      setCanResend(false);
      setSuccess(`Verification code sent to ${email}`);
    }, 800);
  };

  // OTP Handling
  const handleOtpChange = (index, value) => {
    if (!/^\d*$/.test(value)) return;
    const newOtp = [...otp];
    newOtp[index] = value.slice(-1);
    setOtp(newOtp);

    // Auto-focus next input
    if (value && index < 5) {
      const nextInput = document.getElementById(`otp-input-${index + 1}`);
      if (nextInput) nextInput.focus();
    }
  };

  const handleOtpKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      const prevInput = document.getElementById(`otp-input-${index - 1}`);
      if (prevInput) prevInput.focus();
    }
  };

  const handleVerifyOtp = (e) => {
    e.preventDefault();
    const fullOtp = otp.join('');
    if (fullOtp.length < 6) {
      setError({ message: 'Please enter the complete 6-digit verification code.' });
      return;
    }

    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      if (fullOtp === '123456' || fullOtp.length === 6) {
        setSuccess('Authentication successful! Directing to Cafe Rudra menu...');
      } else {
        setError({ message: 'Invalid verification code. Try 123456.' });
      }
    }, 900);
  };

  const handleResendOtp = () => {
    if (!canResend) return;
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      setTimer(45);
      setCanResend(false);
      setSuccess('A fresh 6-digit code has been dispatched to your email.');
    }, 600);
  };

  return (
    <div className="min-h-screen w-full bg-[#0E0E10] text-zinc-100 flex items-center justify-center p-4 relative overflow-hidden font-sans selection:bg-amber-400 selection:text-black">
      
      {/* Background Decorative Ambient Glows */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-amber-500/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-[300px] h-[300px] bg-amber-400/5 rounded-full blur-[100px] pointer-events-none" />

      {/* Main Glassmorphism Floating Modal Card */}
      <div className="w-full max-w-md bg-zinc-900/65 backdrop-blur-xl border border-white/10 rounded-3xl p-8 shadow-[0_20px_50px_rgba(0,0,0,0.5)] relative z-10 transition-all duration-300 hover:border-white/15 hover:shadow-[0_25px_60px_rgba(251,191,36,0.06)]">
        
        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-amber-500/20 to-amber-400/10 border border-amber-500/30 mb-3 shadow-[0_0_20px_rgba(251,191,36,0.15)] group transition-transform hover:scale-105">
            <Utensils className="w-7 h-7 text-amber-400 group-hover:rotate-12 transition-transform duration-300" />
          </div>
          <div className="flex items-center justify-center gap-1.5 text-xs font-semibold uppercase tracking-widest text-amber-400/90 mb-1">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Cafe Rudra</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            {step === 'otp' ? 'Security Verification' : activeTab === 'signin' ? 'Welcome Back' : 'Create an Account'}
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            {step === 'otp'
              ? `Enter the code sent to ${email}`
              : activeTab === 'signin'
              ? 'Enter your email to receive a 6-digit verification code'
              : 'Sign up with your details for fast doorstep delivery'}
          </p>
        </div>

        {/* Sleek Segmented Tab Switcher (Credentials Mode Only) */}
        {step === 'credentials' && (
          <div className="bg-zinc-950/70 p-1.5 rounded-2xl border border-white/5 mb-6 relative flex items-center">
            {/* Sliding Active Tab Background */}
            <div
              className={`absolute top-1.5 bottom-1.5 w-[calc(50%-6px)] bg-amber-400 rounded-xl transition-all duration-300 ease-out shadow-[0_2px_12px_rgba(251,191,36,0.25)] ${
                activeTab === 'signup' ? 'translate-x-[calc(100%+6px)]' : 'translate-x-0'
              }`}
            />
            
            <button
              type="button"
              onClick={() => handleTabSwitch('signin')}
              className={`flex-1 py-2.5 text-xs font-bold rounded-xl relative z-10 transition-colors duration-200 text-center ${
                activeTab === 'signin' ? 'text-zinc-950' : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => handleTabSwitch('signup')}
              className={`flex-1 py-2.5 text-xs font-bold rounded-xl relative z-10 transition-colors duration-200 text-center ${
                activeTab === 'signup' ? 'text-zinc-950' : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Create Account
            </button>
          </div>
        )}

        {/* Success Banner */}
        {success && (
          <div className="mb-5 p-3.5 bg-emerald-500/10 border border-emerald-500/30 rounded-xl flex items-start gap-2.5 text-emerald-400 text-xs animate-in fade-in slide-in-from-top-1 duration-200">
            <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
            <div className="flex-1 font-medium">{success}</div>
          </div>
        )}

        {/* Smart Inline Error Banner with Action Button */}
        {error && (
          <div className="mb-5 p-3.5 bg-amber-500/10 border border-amber-500/30 rounded-xl flex flex-col gap-2 text-amber-300 text-xs animate-in fade-in slide-in-from-top-1 duration-200">
            <div className="flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div className="flex-1 font-medium">{error.message}</div>
            </div>
            
            {error.actionText && error.targetTab && (
              <button
                type="button"
                onClick={() => handleTabSwitch(error.targetTab)}
                className="mt-1 self-end inline-flex items-center gap-1 font-bold text-amber-400 hover:text-amber-300 underline underline-offset-4 text-xs transition-colors"
              >
                <span>{error.actionText}</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            )}
          </div>
        )}

        {/* Form Body */}
        {step === 'credentials' ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            
            {/* Phone Number Field (Create Account mode only) */}
            {activeTab === 'signup' && (
              <div className="space-y-1.5 animate-in fade-in duration-200">
                <label className="text-xs font-semibold text-zinc-300">
                  Phone Number <span className="text-amber-400">*</span>
                </label>
                <div className="relative group">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-zinc-500 group-focus-within:text-amber-400 transition-colors">
                    <Phone className="w-4 h-4" />
                  </div>
                  <input
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+91 98765 43210"
                    required
                    className="w-full pl-10 pr-4 py-3 bg-zinc-950/80 border border-white/10 rounded-xl text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-amber-400 focus:ring-1 focus:ring-amber-400 transition-all"
                  />
                </div>
              </div>
            )}

            {/* Email Address Field */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-zinc-300">
                Email Address <span className="text-amber-400">*</span>
              </label>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-zinc-500 group-focus-within:text-amber-400 transition-colors">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your.email@example.com"
                  required
                  className="w-full pl-10 pr-4 py-3 bg-zinc-950/80 border border-white/10 rounded-xl text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-amber-400 focus:ring-1 focus:ring-amber-400 transition-all"
                />
              </div>
            </div>

            {/* Primary Action Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-2 py-3.5 px-4 bg-amber-400 hover:bg-amber-300 active:scale-[0.99] text-zinc-950 font-bold rounded-xl transition-all shadow-[0_4px_20px_rgba(251,191,36,0.25)] flex items-center justify-center gap-2 group disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <RefreshCw className="w-4 h-4 animate-spin text-zinc-950" />
              ) : (
                <>
                  <span>{activeTab === 'signin' ? 'Send Verification Code' : 'Continue to Menu'}</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>

            {/* Switch Subtext Link */}
            <div className="pt-3 text-center">
              {activeTab === 'signin' ? (
                <button
                  type="button"
                  onClick={() => handleTabSwitch('signup')}
                  className="text-xs text-zinc-400 hover:text-amber-400 transition-colors"
                >
                  New here? <span className="font-semibold text-amber-400 underline underline-offset-2">Create an account</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => handleTabSwitch('signin')}
                  className="text-xs text-zinc-400 hover:text-amber-400 transition-colors"
                >
                  Already have an account? <span className="font-semibold text-amber-400 underline underline-offset-2">Sign in</span>
                </button>
              )}
            </div>

          </form>
        ) : (
          /* Step 2: 6-Digit OTP Verification View */
          <form onSubmit={handleVerifyOtp} className="space-y-6 animate-in fade-in duration-300">
            <div className="flex justify-between items-center text-xs text-zinc-400 mb-1">
              <button
                type="button"
                onClick={() => setStep('credentials')}
                className="inline-flex items-center gap-1 text-zinc-400 hover:text-amber-400 transition-colors"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Change Email</span>
              </button>
              <div className="inline-flex items-center gap-1 text-amber-400/90 font-medium">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Secure OTP</span>
              </div>
            </div>

            {/* 6 OTP Inputs */}
            <div className="flex justify-between gap-2">
              {otp.map((digit, index) => (
                <input
                  key={index}
                  id={`otp-input-${index}`}
                  type="text"
                  maxLength={1}
                  value={digit}
                  onChange={(e) => handleOtpChange(index, e.target.value)}
                  onKeyDown={(e) => handleOtpKeyDown(index, e)}
                  className="w-12 h-14 bg-zinc-950/90 border border-white/15 focus:border-amber-400 focus:ring-1 focus:ring-amber-400 rounded-xl text-center text-xl font-mono font-bold text-amber-400 focus:outline-none transition-all shadow-inner"
                />
              ))}
            </div>

            {/* Verify Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3.5 px-4 bg-amber-400 hover:bg-amber-300 active:scale-[0.99] text-zinc-950 font-bold rounded-xl transition-all shadow-[0_4px_20px_rgba(251,191,36,0.25)] flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <RefreshCw className="w-4 h-4 animate-spin text-zinc-950" />
              ) : (
                <span>Verify & Enter Cafe Rudra</span>
              )}
            </button>

            {/* Resend Timer Subtext */}
            <div className="text-center">
              {canResend ? (
                <button
                  type="button"
                  onClick={handleResendOtp}
                  className="text-xs font-semibold text-amber-400 hover:text-amber-300 underline underline-offset-2 transition-colors"
                >
                  Didn't get code? Resend OTP
                </button>
              ) : (
                <p className="text-xs text-zinc-500">
                  Resend code in <span className="font-mono font-bold text-zinc-300">{timer}s</span>
                </p>
              )}
            </div>
          </form>
        )}

        {/* Footer Security Badge */}
        <div className="mt-8 pt-4 border-t border-white/5 flex items-center justify-center gap-2 text-[11px] text-zinc-500">
          <ShieldCheck className="w-3.5 h-3.5 text-amber-400/70" />
          <span>Encrypted Session • Fast Doorstep Delivery</span>
        </div>

      </div>
    </div>
  );
}

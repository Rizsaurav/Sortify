import React, { useState } from 'react';
import { ArrowLeft, User, Mail, Calendar, Camera, Save, Edit3, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useUserProfile } from '../Dashboard/hooks/useUserProfile';
import type { UserProfile } from '../Dashboard/types';

// Types
interface FormData {
  username: string;
  full_name: string;
  bio: string;
  avatar_url: string;
}

// Component: Avatar Display
const Avatar: React.FC<{ avatarUrl: string; username: string; isEditing: boolean }> = ({ 
  avatarUrl, 
  username, 
  isEditing 
}) => {
  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(word => word.charAt(0))
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <div className="relative inline-block mb-4">
      {avatarUrl ? (
        <img
          src={avatarUrl}
          alt={username}
          className="w-24 h-24 rounded-full object-cover mx-auto"
        />
      ) : (
        <div className="w-24 h-24 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-semibold text-2xl mx-auto">
          {getInitials(username || 'User')}
        </div>
      )}
      {isEditing && (
        <button className="absolute bottom-0 right-0 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center hover:bg-blue-700 transition-colors">
          <Camera className="w-4 h-4" />
        </button>
      )}
    </div>
  );
};

// Component: Profile Card
const ProfileCard: React.FC<{ 
  formData: FormData; 
  email: string; 
  isEditing: boolean 
}> = ({ formData, email, isEditing }) => (
  <div className="bg-card rounded-xl border border-border p-6">
    <div className="text-center">
      <Avatar 
        avatarUrl={formData.avatar_url} 
        username={formData.username} 
        isEditing={isEditing} 
      />
      <h2 className="text-xl font-semibold mb-1">{formData.username || 'User'}</h2>
      <p className="text-muted-foreground text-sm mb-4">{email}</p>
      {formData.bio && (
        <p className="text-sm text-muted-foreground">{formData.bio}</p>
      )}
    </div>
  </div>
);

// Component: Account Information
const AccountInformation: React.FC<{ 
  email: string; 
  createdAt?: string 
}> = ({ email, createdAt }) => (
  <div className="bg-card rounded-xl border border-border p-6 mt-6">
    <h3 className="text-lg font-semibold mb-4">Account Information</h3>
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <Mail className="w-4 h-4 text-muted-foreground" />
        <div>
          <p className="text-sm font-medium">Email</p>
          <p className="text-xs text-muted-foreground">{email}</p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <Calendar className="w-4 h-4 text-muted-foreground" />
        <div>
          <p className="text-sm font-medium">Member Since</p>
          <p className="text-xs text-muted-foreground">
            {createdAt ? new Date(createdAt).toLocaleDateString() : 'Unknown'}
          </p>
        </div>
      </div>
    </div>
  </div>
);

// Component: Form Field
const FormField: React.FC<{
  label: string;
  name: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
  disabled: boolean;
  type?: string;
  rows?: number;
  placeholder?: string;
  helpText?: string;
}> = ({ label, name, value, onChange, disabled, type = 'text', rows, placeholder, helpText }) => {
  const isTextarea = rows !== undefined;
  const InputComponent = isTextarea ? 'textarea' : 'input';

  return (
    <div>
      <label className="block text-sm font-medium mb-2">{label}</label>
      <InputComponent
        type={!isTextarea ? type : undefined}
        name={name}
        value={value}
        onChange={onChange}
        disabled={disabled}
        rows={rows}
        className="w-full p-3 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed resize-none"
        placeholder={placeholder}
      />
      {helpText && (
        <p className="text-xs text-muted-foreground mt-1">{helpText}</p>
      )}
    </div>
  );
};

// Component: Profile Form
const ProfileForm: React.FC<{
  formData: FormData;
  isEditing: boolean;
  onInputChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
  onEdit: () => void;
  onSave: () => void;
  onCancel: () => void;
}> = ({ formData, isEditing, onInputChange, onEdit, onSave, onCancel }) => (
  <div className="bg-card rounded-xl border border-border p-6">
    <div className="flex items-center justify-between mb-6">
      <h3 className="text-lg font-semibold">Profile Details</h3>
      {!isEditing ? (
        <button
          onClick={onEdit}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Edit3 className="w-4 h-4" />
          Edit Profile
        </button>
      ) : (
        <div className="flex items-center gap-2">
          <button
            onClick={onCancel}
            className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
          >
            <X className="w-4 h-4" />
            Cancel
          </button>
          <button
            onClick={onSave}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Save className="w-4 h-4" />
            Save Changes
          </button>
        </div>
      )}
    </div>

    <div className="space-y-6">
      <FormField
        label="Username"
        name="username"
        value={formData.username}
        onChange={onInputChange}
        disabled={!isEditing}
        placeholder="Enter your username"
      />
      <FormField
        label="Full Name"
        name="full_name"
        value={formData.full_name}
        onChange={onInputChange}
        disabled={!isEditing}
        placeholder="Enter your full name"
      />
      <FormField
        label="Bio"
        name="bio"
        value={formData.bio}
        onChange={onInputChange}
        disabled={!isEditing}
        rows={4}
        placeholder="Tell us about yourself..."
      />
      <FormField
        label="Avatar URL"
        name="avatar_url"
        value={formData.avatar_url}
        onChange={onInputChange}
        disabled={!isEditing}
        type="url"
        placeholder="https://example.com/avatar.jpg"
        helpText="Enter a URL to your profile picture"
      />
    </div>
  </div>
);

// Component: Preferences Section
const PreferencesSection: React.FC = () => (
  <div className="bg-card rounded-xl border border-border p-6 mt-6">
    <h3 className="text-lg font-semibold mb-4">Preferences</h3>
    <div className="space-y-4">
      <PreferenceItem
        title="Email Notifications"
        description="Receive updates about your files"
        defaultChecked
      />
      <PreferenceItem
        title="Dark Mode"
        description="Use dark theme"
      />
      <PreferenceItem
        title="Auto-categorization"
        description="Automatically categorize uploaded files"
        defaultChecked
      />
    </div>
  </div>
);

// Component: Preference Item
const PreferenceItem: React.FC<{
  title: string;
  description: string;
  defaultChecked?: boolean;
}> = ({ title, description, defaultChecked = false }) => (
  <div className="flex items-center justify-between">
    <div>
      <p className="text-sm font-medium">{title}</p>
      <p className="text-xs text-muted-foreground">{description}</p>
    </div>
    <input type="checkbox" className="rounded border-border" defaultChecked={defaultChecked} />
  </div>
);

// Component: Danger Zone
const DangerZone: React.FC = () => (
  <div className="bg-card rounded-xl border border-red-200 dark:border-red-800 p-6 mt-6">
    <h3 className="text-lg font-semibold text-red-600 dark:text-red-400 mb-4">Danger Zone</h3>
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-red-600 dark:text-red-400">Delete Account</p>
          <p className="text-xs text-muted-foreground">Permanently delete your account and all data</p>
        </div>
        <button className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors">
          Delete Account
        </button>
      </div>
    </div>
  </div>
);

// Component: Loading State
const LoadingState: React.FC = () => (
  <div className="min-h-screen bg-background flex items-center justify-center">
    <div className="text-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
      <p className="text-muted-foreground">Loading profile...</p>
    </div>
  </div>
);

// Main Component
export default function ProfilePage() {
  const navigate = useNavigate();
  const { userProfile, updateProfile, isLoading } = useUserProfile();
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState<FormData>({
    username: userProfile?.username || '',
    full_name: userProfile?.full_name || '',
    bio: userProfile?.bio || '',
    avatar_url: userProfile?.avatar_url || ''
  });

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSave = async () => {
    try {
      await updateProfile(formData);
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to update profile:', error);
    }
  };

  const handleCancel = () => {
    setFormData({
      username: userProfile?.username || '',
      full_name: userProfile?.full_name || '',
      bio: userProfile?.bio || '',
      avatar_url: userProfile?.avatar_url || ''
    });
    setIsEditing(false);
  };

  if (isLoading) {
    return <LoadingState />;
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <div className="flex items-center gap-4 p-4 lg:p-6 border-b border-border">
        <button
          onClick={() => navigate('/dashboard')}
          className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </button>
        <div className="h-6 w-px bg-border"></div>
        <h1 className="text-2xl font-bold">Profile Settings</h1>
      </div>

      {/* Main Content */}
      <main className="p-4 lg:p-6 max-w-4xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column */}
          <div className="lg:col-span-1">
            <ProfileCard 
              formData={formData} 
              email={userProfile?.email || ''} 
              isEditing={isEditing} 
            />
            <AccountInformation 
              email={userProfile?.email || ''} 
              createdAt={userProfile?.created_at} 
            />
          </div>

          {/* Right Column */}
          <div className="lg:col-span-2">
            <ProfileForm
              formData={formData}
              isEditing={isEditing}
              onInputChange={handleInputChange}
              onEdit={() => setIsEditing(true)}
              onSave={handleSave}
              onCancel={handleCancel}
            />
            <PreferencesSection />
            <DangerZone />
          </div>
        </div>
      </main>
    </div>
  );
}
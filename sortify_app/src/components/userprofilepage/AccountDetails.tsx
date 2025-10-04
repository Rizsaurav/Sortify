import { useState, useRef } from 'react';
import { Button, Input, Label } from './UI/ui-core';
import { Avatar, AvatarImage, AvatarFallback } from './UI/ui-core';
import { Save, Edit2, Upload } from 'lucide-react';

const userProfile = {
  full_name: 'Alex Smith',
  username: 'alex.smith',
  email: 'alex.smith@university.edu',
  bio: 'Computer Science Major',
  hobbies: ['Coding', 'Reading', 'Hiking'],
  interests: ['AI', 'Web Development'],
  avatar_url: '/diverse-student-profiles.png',
};

export default function AccountDetails() {
  const [isEditing, setIsEditing] = useState(false);
  const [profile, setProfile] = useState(userProfile);
  const [previewAvatar, setPreviewAvatar] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleEditToggle = () => {
    setIsEditing(!isEditing);
    if (isEditing) {
      setPreviewAvatar(null); // Reset preview when exiting edit mode
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setProfile((prev) => ({ ...prev, [name]: value }));
  };

  const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const previewUrl = URL.createObjectURL(file);
      setPreviewAvatar(previewUrl);
      // Backend upload logic will be handled separately
      // Example: setProfile((prev) => ({ ...prev, avatar_url: 'new-url-from-backend' }));
    }
  };

  const handleSave = () => {
    // Backend save logic will be handled separately
    if (previewAvatar) {
      // Revoke the preview URL to avoid memory leaks
      URL.revokeObjectURL(previewAvatar);
      setPreviewAvatar(null);
    }
    setIsEditing(false);
  };

  return (
    <div className="min-h-screen bg-background p-4 lg:p-6">
      <main className="max-w-4xl mx-auto">
        <div className="bg-card rounded-xl border border-border shadow-lg p-6 lg:p-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-foreground">Account Details</h2>
            <Button
              variant={isEditing ? 'default' : 'ghost'}
              size="sm"
              onClick={isEditing ? handleSave : handleEditToggle}
              className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white"
            >
              {isEditing ? (
                <>
                  <Save className="w-4 h-4" />
                  Save Changes
                </>
              ) : (
                <>
                  <Edit2 className="w-4 h-4" />
                  Edit Profile
                </>
              )}
            </Button>
          </div>

          <div className="space-y-6">
            {/* Avatar and Basic Info */}
            <div className="flex items-center gap-4">
              <div className="relative">
                <Avatar className="h-16 w-16">
                  <AvatarImage src={previewAvatar || profile.avatar_url} alt={profile.full_name} />
                  <AvatarFallback>
                    {profile.full_name
                      .split(' ')
                      .map((n) => n[0])
                      .join('')}
                  </AvatarFallback>
                </Avatar>
                {isEditing && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute bottom-0 right-0 bg-muted/50 dark:bg-input/30 rounded-full"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <Upload className="w-4 h-4" />
                  </Button>
                )}
                <input
                  type="file"
                  accept="image/*"
                  ref={fileInputRef}
                  className="hidden"
                  onChange={handleAvatarChange}
                />
              </div>
              <div>
                <h3 className="text-lg font-semibold">{profile.full_name}</h3>
                <p className="text-sm text-muted-foreground">@{profile.username}</p>
              </div>
            </div>

            {/* Form Fields */}
            <div className="grid gap-4">
              <div>
                <Label htmlFor="full_name" className="text-sm font-medium">
                  Full Name
                </Label>
                <Input
                  id="full_name"
                  name="full_name"
                  value={profile.full_name}
                  onChange={handleInputChange}
                  disabled={!isEditing}
                  className="mt-1 rounded-lg border-border bg-muted/50 dark:bg-input/30"
                />
              </div>
              <div>
                <Label htmlFor="username" className="text-sm font-medium">
                  Username
                </Label>
                <Input
                  id="username"
                  name="username"
                  value={profile.username}
                  onChange={handleInputChange}
                  disabled={!isEditing}
                  className="mt-1 rounded-lg border-border bg-muted/50 dark:bg-input/30"
                />
              </div>
              <div>
                <Label htmlFor="email" className="text-sm font-medium">
                  Email
                </Label>
                <Input
                  id="email"
                  name="email"
                  value={profile.email}
                  disabled
                  className="mt-1 rounded-lg border-border bg-muted/50 dark:bg-input/30 opacity-50"
                />
              </div>
              <div>
                <Label htmlFor="bio" className="text-sm font-medium">
                  Bio
                </Label>
                <textarea
                  id="bio"
                  name="bio"
                  value={profile.bio}
                  onChange={handleInputChange}
                  disabled={!isEditing}
                  className="mt-1 w-full rounded-lg border border-border bg-muted/50 dark:bg-input/30 p-2 text-sm"
                  rows={4}
                />
              </div>
              <div>
                <Label htmlFor="hobbies" className="text-sm font-medium">
                  Hobbies
                </Label>
                <Input
                  id="hobbies"
                  name="hobbies"
                  value={profile.hobbies.join(', ')}
                  onChange={(e) =>
                    setProfile((prev) => ({
                      ...prev,
                      hobbies: e.target.value.split(',').map((h) => h.trim()),
                    }))
                  }
                  disabled={!isEditing}
                  className="mt-1 rounded-lg border-border bg-muted/50 dark:bg-input/30"
                />
              </div>
              <div>
                <Label htmlFor="interests" className="text-sm font-medium">
                  Interests
                </Label>
                <Input
                  id="interests"
                  name="interests"
                  value={profile.interests.join(', ')}
                  onChange={(e) =>
                    setProfile((prev) => ({
                      ...prev,
                      interests: e.target.value.split(',').map((i) => i.trim()),
                    }))
                  }
                  disabled={!isEditing}
                  className="mt-1 rounded-lg border-border bg-muted/50 dark:bg-input/30"
                />
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
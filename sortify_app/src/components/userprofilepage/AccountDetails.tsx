import { useState, useRef } from "react";
import { Button, Avatar, AvatarImage, AvatarFallback } from "../landing_page/UI/ui-core";
import { Save, Edit2 } from "lucide-react";

// Sample profile data
const userProfile = {
  fullname: "Alex Smith",
  username: "alex.smith",
  email: "alex.smith@university.edu",
  bio: "Computer Science Major",
  hobbies: "Coding, Reading, Hiking",
  interests: "AI, Web Development",
  avatarurl: "/diverse-student-profiles.png",
};

export default function AccountDetails() {
  const [isEditing, setIsEditing] = useState(false);
  const [profile, setProfile] = useState(userProfile);
  const [previewAvatar, setPreviewAvatar] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleEditToggle = () => {
    setIsEditing(!isEditing);
    if (isEditing) setPreviewAvatar(null);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setProfile((prev) => ({ ...prev, [name]: value }));
  };

  const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const reader = new FileReader();
      reader.onload = (event) => setPreviewAvatar(event.target?.result as string);
      reader.readAsDataURL(file);
    }
  };

  const handleSaveProfile = () => {
    setIsEditing(false);
    if (previewAvatar) setProfile((prev) => ({ ...prev, avatarurl: previewAvatar }));
    setPreviewAvatar(null);
  };

  return (
    <div className="account-details-page">
      <h2>Account Details</h2>
      <Avatar className="h-20 w-20">
        <AvatarImage src={previewAvatar ?? profile.avatarurl} alt={profile.fullname} />
        <AvatarFallback>
          {profile.fullname
            .split(" ")
            .map((word) => word[0])
            .join("")
            .toUpperCase()}
        </AvatarFallback>
      </Avatar>
      {isEditing && (
        <input type="file" ref={fileInputRef} onChange={handleAvatarChange} />
      )}

      <div>
        <div>
          <strong>Full Name:</strong>
          <input
            name="fullname"
            value={profile.fullname}
            onChange={handleInputChange}
            disabled={!isEditing}
          />
        </div>
        <div>
          <strong>Username:</strong>
          <input
            name="username"
            value={profile.username}
            onChange={handleInputChange}
            disabled={!isEditing}
          />
        </div>
        <div>
          <strong>Email:</strong>
          <input
            name="email"
            value={profile.email}
            onChange={handleInputChange}
            disabled={!isEditing}
          />
        </div>
        <div>
          <strong>Bio:</strong>
          <input
            name="bio"
            value={profile.bio}
            onChange={handleInputChange}
            disabled={!isEditing}
          />
        </div>
        <div>
          <strong>Hobbies:</strong>
          <input
            name="hobbies"
            value={profile.hobbies}
            onChange={handleInputChange}
            disabled={!isEditing}
          />
        </div>
        <div>
          <strong>Interests:</strong>
          <input
            name="interests"
            value={profile.interests}
            onChange={handleInputChange}
            disabled={!isEditing}
          />
        </div>
      </div>
      <div>
        {isEditing ? (
          <Button onClick={handleSaveProfile}><Save /> Save</Button>
        ) : (
          <Button onClick={handleEditToggle}><Edit2 /> Edit</Button>
        )}
      </div>
    </div>
  );
}

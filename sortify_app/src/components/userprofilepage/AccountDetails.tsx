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
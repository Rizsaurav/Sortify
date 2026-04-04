export interface Category {
  id: number;
  label: string;
  color?: string;
  user_created?: boolean;
  type?: string; // Add this field
}

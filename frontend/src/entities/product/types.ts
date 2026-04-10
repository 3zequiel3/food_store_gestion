/**
 * Product entity types
 */

export interface Ingredient {
  id: string
  name: string
  quantity: number
  unit: string
}

export interface Category {
  id: string
  name: string
  description?: string
  image?: string
}

export interface Product {
  id: string
  name: string
  description?: string
  price: number
  image?: string
  category: Category
  ingredients?: Ingredient[]
  stock: number
  isActive: boolean
  createdAt?: string
  updatedAt?: string
}

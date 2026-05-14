import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ProductDetailPage } from '../ProductDetailPage';
import type { ProductoDetail } from '../../../features/products/types/products.types';

// Mock react-router-dom
vi.mock('react-router-dom', () => ({
  useParams: vi.fn(() => ({ id: '1' })),
  useNavigate: vi.fn(() => vi.fn()),
}));

// Mock the useProduct hook
vi.mock('../../../features/products/hooks/useProduct', () => ({
  useProduct: vi.fn(),
}));

// Mock useCartStore
vi.mock('../../../features/cart/stores/cartStore', () => ({
  useCartStore: vi.fn(() => ({
    getState: vi.fn(() => ({
      addItem: vi.fn(),
    })),
  })),
}));

// Mock axios
vi.mock('axios', () => ({
  isAxiosError: vi.fn((err) => err?.isAxios === true),
}));

import { useProduct } from '../../../features/products/hooks/useProduct';
import { useParams } from 'react-router-dom';

function createMockDetail(overrides?: Partial<ProductoDetail>): ProductoDetail {
  return {
    id: 1,
    nombre: 'Test Product',
    descripcion: 'Test description',
    precio: 10.5,
    imagen_url: null,
    disponible: true,
    stock_cantidad: 5,
    categoria_id: null,
    imagenes: [],
    categorias: [],
    ingredientes: [],
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('ProductDetailPage — image carousel (8.1)', () => {
  it('shows single image without carousel when only 1 image', () => {
    vi.mocked(useProduct).mockReturnValue({
      data: createMockDetail({
        imagenes: [{ id: 1, url: 'https://example.com/single.jpg', orden: 0, es_primaria: true }],
      }),
      isLoading: false,
      error: null,
    } as any);

    render(<ProductDetailPage />);

    // Should show the image
    expect(screen.getByAltText('Test Product')).toBeInTheDocument();
    // Should NOT show thumbnail strip
    expect(screen.queryByTestId('thumbnail-strip')).not.toBeInTheDocument();
  });

  it('shows carousel with thumbnail strip when multiple images', () => {
    vi.mocked(useProduct).mockReturnValue({
      data: createMockDetail({
        imagenes: [
          { id: 1, url: 'https://example.com/img1.jpg', orden: 0, es_primaria: true },
          { id: 2, url: 'https://example.com/img2.jpg', orden: 1, es_primaria: false },
          { id: 3, url: 'https://example.com/img3.jpg', orden: 2, es_primaria: false },
        ],
      }),
      isLoading: false,
      error: null,
    } as any);

    render(<ProductDetailPage />);

    // Should show thumbnail strip
    expect(screen.getByTestId('thumbnail-strip')).toBeInTheDocument();
    // Should show 3 thumbnails
    expect(screen.getAllByTestId('thumbnail-item')).toHaveLength(3);
  });

  it('click on thumbnail changes main image', () => {
    vi.mocked(useProduct).mockReturnValue({
      data: createMockDetail({
        imagenes: [
          { id: 1, url: 'https://example.com/img1.jpg', orden: 0, es_primaria: true },
          { id: 2, url: 'https://example.com/img2.jpg', orden: 1, es_primaria: false },
        ],
      }),
      isLoading: false,
      error: null,
    } as any);

    render(<ProductDetailPage />);

    // Initially shows primary image
    const mainImageContainer = screen.getByTestId('main-image');
    const mainImage = mainImageContainer.querySelector('img');
    expect(mainImage).toHaveAttribute('src', 'https://example.com/img1.jpg');

    // Click second thumbnail
    const thumbnails = screen.getAllByTestId('thumbnail-item');
    fireEvent.click(thumbnails[1]);

    // Main image should now show second image
    const updatedMainImage = screen.getByTestId('main-image').querySelector('img');
    expect(updatedMainImage).toHaveAttribute('src', 'https://example.com/img2.jpg');
  });

  it('shows first image by orden when no primary is set', () => {
    vi.mocked(useProduct).mockReturnValue({
      data: createMockDetail({
        imagenes: [
          { id: 1, url: 'https://example.com/img1.jpg', orden: 1, es_primaria: false },
          { id: 2, url: 'https://example.com/img2.jpg', orden: 0, es_primaria: false },
        ],
      }),
      isLoading: false,
      error: null,
    } as any);

    render(<ProductDetailPage />);

    const mainImageContainer = screen.getByTestId('main-image');
    const mainImage = mainImageContainer.querySelector('img');
    // Should show the one with orden=0 (first by orden)
    expect(mainImage).toHaveAttribute('src', 'https://example.com/img2.jpg');
  });

  it('highlights active thumbnail', () => {
    vi.mocked(useProduct).mockReturnValue({
      data: createMockDetail({
        imagenes: [
          { id: 1, url: 'https://example.com/img1.jpg', orden: 0, es_primaria: true },
          { id: 2, url: 'https://example.com/img2.jpg', orden: 1, es_primaria: false },
        ],
      }),
      isLoading: false,
      error: null,
    } as any);

    render(<ProductDetailPage />);

    const thumbnails = screen.getAllByTestId('thumbnail-item');
    // First thumbnail should be active
    expect(thumbnails[0]).toHaveClass('ring-2');

    // Click second thumbnail
    fireEvent.click(thumbnails[1]);

    // Second should now be active
    const updatedThumbnails = screen.getAllByTestId('thumbnail-item');
    expect(updatedThumbnails[1]).toHaveClass('ring-2');
  });

  it('shows no images section when product has no images', () => {
    vi.mocked(useProduct).mockReturnValue({
      data: createMockDetail({ imagenes: [] }),
      isLoading: false,
      error: null,
    } as any);

    render(<ProductDetailPage />);

    // Should show placeholder
    expect(screen.getByTestId('image-placeholder')).toBeInTheDocument();
    // No carousel
    expect(screen.queryByTestId('thumbnail-strip')).not.toBeInTheDocument();
  });
});

import { useState, type ReactNode } from 'react';
import { resolveImageUrl } from '../../../lib/images';

interface ProductImageProps {
  src?: string | null;
  alt: string;
  className?: string;
  placeholder: ReactNode;
  loading?: 'eager' | 'lazy';
}

export function ProductImage({
  src,
  alt,
  className,
  placeholder,
  loading = 'lazy',
}: ProductImageProps) {
  const imageSrc = resolveImageUrl(src);
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const shouldRenderImage = imageSrc && failedSrc !== imageSrc;

  if (!shouldRenderImage) {
    return placeholder;
  }

  return (
    <img
      src={imageSrc}
      alt={alt}
      loading={loading}
      crossOrigin="anonymous"
      onError={() => setFailedSrc(imageSrc)}
      className={className}
    />
  );
}

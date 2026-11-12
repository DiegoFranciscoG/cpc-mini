/** Título y descripción por página (SEO y lectores de pantalla). */
import {useEffect} from 'react';

export const SITE_NAME = 'CPC-mini';

export function usePageMeta(title: string, description: string): void {
  useEffect(() => {
    document.title = title === SITE_NAME ? title : `${title} | ${SITE_NAME}`;
    let tag = document.querySelector<HTMLMetaElement>('meta[name="description"]');
    if (!tag) {
      tag = document.createElement('meta');
      tag.name = 'description';
      document.head.appendChild(tag);
    }
    tag.content = description;
  }, [title, description]);
}

const percent = new Intl.NumberFormat('es-EC', {style: 'percent', maximumFractionDigits: 1});
const integer = new Intl.NumberFormat('es-EC');
const decimal = new Intl.NumberFormat('es-EC', {minimumFractionDigits: 1, maximumFractionDigits: 1});

export function formatPercent(value: number): string {
  return percent.format(value);
}

export function formatInteger(value: number): string {
  return integer.format(value);
}

export function formatDecimal(value: number): string {
  return decimal.format(value);
}

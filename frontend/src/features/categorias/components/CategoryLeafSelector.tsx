import { useState, useRef, useEffect } from 'react';
import { ChevronDown, X, Search } from 'lucide-react';
import { useCategorias } from '../hooks/useCategorias';
import type { CategoriaTreeNode } from '../types/categorias.types';

interface Props {
  value: number[];
  onChange: (ids: number[]) => void;
}

function collectLeaves(nodes: CategoriaTreeNode[]): CategoriaTreeNode[] {
  return nodes.flatMap((n) =>
    n.subcategorias.length === 0 ? [n] : collectLeaves(n.subcategorias),
  );
}

function TreeNodeRow({
  node,
  level,
  search,
  selected,
  onToggle,
}: {
  node: CategoriaTreeNode;
  level: number;
  search: string;
  selected: Set<number>;
  onToggle: (id: number) => void;
}) {
  const isLeaf = node.subcategorias.length === 0;
  const [open, setOpen] = useState(true);

  const matchesSearch = node.nombre.toLowerCase().includes(search.toLowerCase());
  const childrenMatchSearch = (nodes: CategoriaTreeNode[]): boolean =>
    nodes.some(
      (n) =>
        n.nombre.toLowerCase().includes(search.toLowerCase()) ||
        childrenMatchSearch(n.subcategorias),
    );

  if (search && !matchesSearch && !childrenMatchSearch(node.subcategorias)) return null;

  if (isLeaf) {
    const isSelected = selected.has(node.id);
    return (
      <button
        type="button"
        onClick={() => onToggle(node.id)}
        className={`w-full text-left px-3 py-1.5 text-sm rounded flex items-center gap-2 transition-colors ${
          isSelected
            ? 'bg-orange-100 text-orange-700 font-medium'
            : 'hover:bg-gray-100 text-gray-700'
        }`}
        style={{ paddingLeft: `${12 + level * 16}px` }}
      >
        <span
          className={`w-3.5 h-3.5 rounded border flex-shrink-0 flex items-center justify-center ${
            isSelected ? 'bg-orange-500 border-orange-500' : 'border-gray-300'
          }`}
        >
          {isSelected && (
            <svg viewBox="0 0 8 8" className="w-2 h-2 text-white fill-current">
              <path d="M1 4l2 2 4-4" stroke="currentColor" strokeWidth="1.5" fill="none" />
            </svg>
          )}
        </span>
        {node.nombre}
      </button>
    );
  }

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((p) => !p)}
        className="w-full text-left px-3 py-1.5 text-sm font-semibold text-gray-500 flex items-center gap-1 hover:text-gray-700 transition-colors"
        style={{ paddingLeft: `${12 + level * 16}px` }}
      >
        <ChevronDown
          className={`w-3.5 h-3.5 transition-transform ${open ? '' : '-rotate-90'}`}
        />
        {node.nombre}
      </button>
      {open &&
        node.subcategorias.map((child) => (
          <TreeNodeRow
            key={child.id}
            node={child}
            level={level + 1}
            search={search}
            selected={selected}
            onToggle={onToggle}
          />
        ))}
    </div>
  );
}

export function CategoryLeafSelector({ value, onChange }: Props) {
  const { data: tree = [], isLoading } = useCategorias();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);

  const selected = new Set(value);
  const allLeaves = collectLeaves(tree);
  const selectedLeaves = allLeaves.filter((l) => selected.has(l.id));

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  function toggle(id: number) {
    if (selected.has(id)) {
      onChange(value.filter((v) => v !== id));
    } else {
      onChange([...value, id]);
    }
  }

  function remove(id: number) {
    onChange(value.filter((v) => v !== id));
  }

  return (
    <div ref={containerRef} className="relative">
      <div
        role="button"
        tabIndex={0}
        onClick={() => setOpen((p) => !p)}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setOpen((p) => !p); }}
        className="w-full min-h-[40px] px-3 py-2 border border-gray-300 rounded-lg text-sm text-left flex items-center justify-between gap-2 focus:outline-none focus:ring-2 focus:ring-orange-400 bg-white cursor-pointer"
      >
        <span className="flex flex-wrap gap-1 flex-1">
          {selectedLeaves.length === 0 ? (
            <span className="text-gray-400">Seleccioná categorías…</span>
          ) : (
            selectedLeaves.map((l) => (
              <span
                key={l.id}
                className="inline-flex items-center gap-1 bg-orange-100 text-orange-700 text-xs px-2 py-0.5 rounded-full"
              >
                {l.nombre}
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    remove(l.id);
                  }}
                  className="hover:text-orange-900"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))
          )}
        </span>
        <ChevronDown className={`w-4 h-4 text-gray-400 flex-shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </div>

      {open && (
        <div className="absolute z-50 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-64 overflow-y-auto">
          <div className="p-2 border-b border-gray-100 sticky top-0 bg-white">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
              <input
                type="text"
                placeholder="Buscar…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-7 pr-3 py-1.5 text-sm border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-orange-400"
              />
            </div>
          </div>
          {isLoading ? (
            <p className="text-sm text-gray-500 p-3">Cargando…</p>
          ) : tree.length === 0 ? (
            <p className="text-sm text-gray-500 p-3">No hay categorías</p>
          ) : (
            <div className="py-1">
              {tree.map((node) => (
                <TreeNodeRow
                  key={node.id}
                  node={node}
                  level={0}
                  search={search}
                  selected={selected}
                  onToggle={toggle}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

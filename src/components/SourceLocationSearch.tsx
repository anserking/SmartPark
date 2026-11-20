import { useEffect, useId, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { Crosshair, Loader2, MapPin, Search } from 'lucide-react';

import { searchDestinations } from '@/services/destinations';
import type { Coordinate, Destination } from '@/types/smartpark';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export type SourceSelection = { name: string; location: Coordinate };

type Props = {
  currentLocation: Coordinate | null;
  selected: SourceSelection | null;
  onSelect: (source: SourceSelection | null) => void;
  pickingOnMap: boolean;
  onToggleMapPick: () => void;
  disabled?: boolean;
};

export default function SourceLocationSearch({ currentLocation, selected, onSelect, pickingOnMap, onToggleMapPick, disabled = false }: Props) {
  const listId = useId();
  const [query, setQuery] = useState(selected?.name ?? '');
  const [results, setResults] = useState<Destination[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  useEffect(() => { setQuery(selected?.name ?? ''); }, [selected?.name]);

  useEffect(() => {
    const text = query.trim();
    if (disabled || text.length < 2 || text === selected?.name) {
      setResults([]);
      setLoading(false);
      setOpen(false);
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        const found = await searchDestinations(text, {
          bias: currentLocation ?? undefined,
          signal: controller.signal,
        });
        if (!controller.signal.aborted) {
          setResults(found);
          setActiveIndex(-1);
          setOpen(true);
        }
      } catch (cause) {
        if (!controller.signal.aborted) {
          setError(cause instanceof Error ? cause.message : 'Source search is unavailable.');
          setOpen(true);
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, 300);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [query, selected?.name, currentLocation?.latitude, currentLocation?.longitude, disabled]);

  const choose = (place: Destination) => {
    onSelect({ name: place.name, location: place.location });
    setQuery(place.name);
    setOpen(false);
    setActiveIndex(-1);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Escape') {
      setOpen(false);
      return;
    }
    if (!open || results.length === 0) return;
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveIndex((index) => (index + 1) % results.length);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveIndex((index) => index <= 0 ? results.length - 1 : index - 1);
    } else if (event.key === 'Enter' && activeIndex >= 0) {
      event.preventDefault();
      choose(results[activeIndex]);
    }
  };

  return <div className="relative mt-4">
    <label htmlFor={`${listId}-input`} className="mb-2 block text-sm font-medium">Starting location</label>
    <div className="relative">
      <Search aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        id={`${listId}-input`}
        value={query}
        placeholder={currentLocation ? 'Current location or search a place' : 'Search a starting place'}
        autoComplete="off"
        role="combobox"
        disabled={disabled}
        aria-autocomplete="list"
        aria-expanded={open}
        aria-controls={listId}
        aria-activedescendant={activeIndex >= 0 ? `${listId}-option-${activeIndex}` : undefined}
        onChange={(event) => { setQuery(event.target.value); setOpen(true); setError(null); setActiveIndex(-1); }}
        onKeyDown={handleKeyDown}
        className="pl-10"
      />
      {loading && <Loader2 aria-label="Searching starting places" className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin" />}
    </div>
    {open && query.trim().length >= 2 && <ul id={listId} role="listbox" aria-label="Starting place suggestions" className="absolute z-30 mt-1 max-h-60 w-full overflow-y-auto rounded-md border bg-background p-1 shadow-lg">
      {error ? <li role="alert" className="px-3 py-2 text-sm text-destructive">{error}</li> : !loading && results.length === 0 ? <li className="px-3 py-2 text-sm text-muted-foreground">No matching places found.</li> : results.map((place, index) => <li key={place.id} role="presentation">
        <button id={`${listId}-option-${index}`} type="button" role="option" aria-selected={index === activeIndex} className="flex min-h-11 w-full items-start gap-2 rounded px-3 py-2 text-left hover:bg-accent focus-visible:bg-accent" onMouseDown={(event) => event.preventDefault()} onClick={() => choose(place)}>
          <MapPin aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
          <span className="min-w-0"><span className="block truncate text-sm font-medium">{place.name}</span>{place.address && <span className="block truncate text-xs text-muted-foreground">{place.address}</span>}</span>
        </button>
      </li>)}
    </ul>}
    <div className="mt-2 flex flex-wrap gap-2">
      <Button type="button" variant="outline" size="sm" disabled={disabled || !currentLocation} onClick={() => { onSelect(null); setQuery(''); setOpen(false); }}>
        <Crosshair aria-hidden="true" className="mr-1 h-4 w-4" />Use my location
      </Button>
      <Button type="button" variant={pickingOnMap ? 'default' : 'outline'} size="sm" disabled={disabled} aria-pressed={pickingOnMap} onClick={onToggleMapPick}>
        <MapPin aria-hidden="true" className="mr-1 h-4 w-4" />{pickingOnMap ? 'Click a point on the map' : 'Choose on map'}
      </Button>
    </div>
    <p className="mt-2 text-xs text-[#625d51]" aria-live="polite">
      {selected ? `Starting from ${selected.name}` : currentLocation ? 'Starting from your current location' : 'Choose a starting location to plan a driving route.'}
    </p>
  </div>;
}

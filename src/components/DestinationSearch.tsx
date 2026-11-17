import { useEffect, useId, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { Loader2, MapPin, Search } from 'lucide-react';

import { ApiError } from '@/services/api';
import { searchDestinations } from '@/services/destinations';
import { useNavigationStore } from '@/stores/navigationStore';
import type { Coordinate, Destination } from '@/types/smartpark';
import { Input } from '@/components/ui/input';

type DestinationSearchProps = {
  bias?: Coordinate;
};

const minimumQueryLength = 2;
const debounceMilliseconds = 300;

export default function DestinationSearch({ bias }: DestinationSearchProps) {
  const listboxId = useId();
  const selectedDestination = useNavigationStore(
    (state) => state.selectedDestination,
  );
  const selectDestination = useNavigationStore(
    (state) => state.selectDestination,
  );
  const clearDestination = useNavigationStore(
    (state) => state.clearDestination,
  );
  const [query, setQuery] = useState(selectedDestination?.name ?? '');
  const [results, setResults] = useState<Destination[]>([]);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const normalizedQuery = query.trim();
    if (
      normalizedQuery.length < minimumQueryLength ||
      normalizedQuery === selectedDestination?.name
    ) {
      setResults([]);
      setIsLoading(false);
      setError(null);
      setIsOpen(false);
      return;
    }

    const controller = new AbortController();
    const timeoutId = window.setTimeout(async () => {
      setIsLoading(true);
      setError(null);
      try {
        const destinations = await searchDestinations(normalizedQuery, {
          bias,
          signal: controller.signal,
        });
        if (!controller.signal.aborted) {
          setResults(destinations);
          setActiveIndex(-1);
          setIsOpen(true);
        }
      } catch (searchError) {
        if (!controller.signal.aborted) {
          setResults([]);
          setError(
            searchError instanceof ApiError
              ? searchError.message
              : 'Destination search is unavailable. Try again.',
          );
          setIsOpen(true);
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }, debounceMilliseconds);

    return () => {
      window.clearTimeout(timeoutId);
      controller.abort();
    };
  }, [bias, query, selectedDestination?.name]);

  const handleSelect = (destination: Destination) => {
    selectDestination(destination);
    setQuery(destination.name);
    setResults([]);
    setIsOpen(false);
    setActiveIndex(-1);
  };

  const handleChange = (value: string) => {
    if (selectedDestination) {
      clearDestination();
    }
    setQuery(value);
    setResults([]);
    setError(null);
    setIsLoading(value.trim().length >= minimumQueryLength);
    setIsOpen(true);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Escape') {
      setIsOpen(false);
      setActiveIndex(-1);
      return;
    }

    if (!isOpen || results.length === 0) {
      return;
    }

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveIndex((index) => (index + 1) % results.length);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveIndex((index) => (index <= 0 ? results.length - 1 : index - 1));
    } else if (event.key === 'Enter' && activeIndex >= 0) {
      event.preventDefault();
      handleSelect(results[activeIndex]);
    }
  };

  const activeOptionId =
    activeIndex >= 0 ? `${listboxId}-option-${activeIndex}` : undefined;

  return (
    <div className="relative w-full max-w-2xl">
      <label htmlFor={`${listboxId}-input`} className="mb-2 block text-sm font-medium">
        Search for a destination
      </label>
      <div className="relative">
        <Search
          aria-hidden="true"
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
        />
        <Input
          id={`${listboxId}-input`}
          value={query}
          placeholder="For example, Bahria University Karachi"
          autoComplete="off"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={isOpen}
          aria-controls={listboxId}
          aria-activedescendant={activeOptionId}
          onChange={(event) => handleChange(event.target.value)}
          onFocus={() => {
            if (query.trim().length >= minimumQueryLength) {
              setIsOpen(true);
            }
          }}
          onKeyDown={handleKeyDown}
          className="pl-10"
        />
        {isLoading && (
          <Loader2
            aria-label="Searching destinations"
            className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin"
          />
        )}
      </div>
      {isOpen && query.trim().length >= minimumQueryLength && (
        <ul
          id={listboxId}
          role="listbox"
          aria-label="Destination suggestions"
          className="absolute z-20 mt-1 max-h-72 w-full overflow-y-auto rounded-md border bg-background p-1"
        >
          {error ? (
            <li role="alert" className="px-3 py-2 text-sm text-destructive">
              {error}
            </li>
          ) : !isLoading && results.length === 0 ? (
            <li className="px-3 py-2 text-sm text-muted-foreground">
              No matching destinations found.
            </li>
          ) : (
            results.map((destination, index) => (
              <li key={destination.id} role="presentation">
                <button
                  id={`${listboxId}-option-${index}`}
                  type="button"
                  role="option"
                  aria-selected={index === activeIndex}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => handleSelect(destination)}
                  className="flex min-h-11 w-full items-start gap-3 rounded-sm px-3 py-2 text-left hover:bg-accent focus-visible:bg-accent focus-visible:outline-none"
                >
                  <MapPin
                    aria-hidden="true"
                    className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
                  />
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium">
                      {destination.name}
                    </span>
                    {destination.address && (
                      <span className="block truncate text-xs text-muted-foreground">
                        {destination.address}
                      </span>
                    )}
                  </span>
                </button>
              </li>
            ))
          )}
        </ul>
      )}
      {selectedDestination && (
        <p className="mt-2 text-sm text-muted-foreground" aria-live="polite">
          Selected: <span className="font-medium text-foreground">{selectedDestination.name}</span>
          {selectedDestination.address ? ` — ${selectedDestination.address}` : ''}
        </p>
      )}
    </div>
  );
}

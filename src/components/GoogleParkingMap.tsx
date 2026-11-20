import { useEffect, useRef, useState } from 'react';
import { loadMaps, type MapView, type Marker, type MapsApi } from './GoogleSmartParkMap';
import type { ParkingSpot } from '@/types';

type Location = { latitude: number; longitude: number };

type Props = {
  center: Location;
  spots?: ParkingSpot[];
  selectedLocation?: { lat: number; lng: number } | null;
  onSelectSpot?: (spot: ParkingSpot) => void;
  onLocationChange?: (point: { lat: number; lng: number }) => void;
};

export default function GoogleParkingMap({ center, spots, selectedLocation, onSelectSpot, onLocationChange }: Props) {
  const elementRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapView | null>(null);
  const markersRef = useRef<Marker[]>([]);
  const [maps, setMaps] = useState<MapsApi | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void loadMaps().then((api) => {
      if (cancelled || !elementRef.current) return;
      mapRef.current = new api.Map(elementRef.current, {
        center: { lat: center.latitude, lng: center.longitude },
        zoom: onLocationChange ? 15 : 13,
        mapTypeControl: false,
        streetViewControl: false,
      });
      setMaps(api);
    }).catch((cause: unknown) => {
      if (!cancelled) setError(cause instanceof Error ? cause.message : 'Google map unavailable.');
    });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!maps || !mapRef.current) return;
    const map = mapRef.current;
    map.setCenter({ lat: center.latitude, lng: center.longitude });
    for (const marker of markersRef.current) marker.setMap(null);
    markersRef.current = [];
    const add = (position: { lat: number; lng: number }, label: string, title: string, draggable = false) => {
      const marker = new maps.Marker({ map, position, label, title, draggable });
      markersRef.current.push(marker);
      return marker;
    };
    if (onLocationChange) {
      const marker = add(selectedLocation ?? { lat: center.latitude, lng: center.longitude }, 'P', 'Parking location', true);
      marker.addListener('dragend', () => {
        const point = marker.getPosition();
        if (point) onLocationChange({ lat: point.lat(), lng: point.lng() });
      });
    } else {
      add({ lat: center.latitude, lng: center.longitude }, 'U', 'Your location');
      for (const spot of spots ?? []) {
        const marker = add({ lat: spot.location.latitude, lng: spot.location.longitude }, 'P', `${spot.type} parking`);
        marker.addListener('click', () => onSelectSpot?.(spot));
      }
    }
    return () => {
      for (const marker of markersRef.current) marker.setMap(null);
      markersRef.current = [];
    };
  }, [maps, center.latitude, center.longitude, spots, selectedLocation?.lat, selectedLocation?.lng, onSelectSpot, onLocationChange]);

  return <div className="relative h-full w-full">
    <div ref={elementRef} className="h-full w-full" aria-label="Google map of parking" />
    {error && <p role="alert" className="absolute bottom-4 left-4 rounded bg-white p-3 text-sm text-red-700">{error}</p>}
  </div>;
}

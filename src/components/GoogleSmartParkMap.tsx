import { useEffect, useRef, useState } from 'react';
import { useNavigationStore } from '@/stores/navigationStore';
import type { Coordinate, ParkingRecommendation } from '@/types/smartpark';

export type Point = { lat: number; lng: number };
export type Overlay = { setMap(map: null): void };
type MapClickEvent = { latLng?: { lat(): number; lng(): number } };
export type MapView = { setCenter(point: Point): void; fitBounds(bounds: Bounds): void; addListener(event: string, callback: (event: MapClickEvent) => void): { remove(): void } };
export type Marker = Overlay & { addListener(event: string, callback: () => void): void; getPosition(): { lat(): number; lng(): number } | null };
export type Bounds = { extend(point: Point): void };
export type MapsApi = {
  Map: new (element: HTMLElement, options: object) => MapView;
  Marker: new (options: object) => Marker;
  Polyline: new (options: object) => Overlay;
  LatLngBounds: new () => Bounds;
};

declare global {
  interface Window {
    google?: { maps: MapsApi };
  }
}

let mapsPromise: Promise<MapsApi> | null = null;

export function loadMaps(): Promise<MapsApi> {
  if (window.google?.maps) return Promise.resolve(window.google.maps);
  if (mapsPromise) return mapsPromise;
  const key = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
  if (!key) return Promise.reject(new Error('Google Maps browser key is missing.'));
  mapsPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(key)}&v=weekly`;
    script.async = true;
    script.onload = () => {
      if (window.google?.maps) resolve(window.google.maps);
      else reject(new Error('Google Maps did not initialize.'));
    };
    script.onerror = () => reject(new Error('Google Maps could not load.'));
    document.head.append(script);
  });
  return mapsPromise;
}

const point = (location: Coordinate): Point => ({
  lat: location.latitude,
  lng: location.longitude,
});

type Props = {
  userLocation: Coordinate | null;
  sourceName?: string;
  parkingFacilities: ParkingRecommendation[];
  selectedSpotId: string | null;
  onSelectSpot: (spot: ParkingRecommendation) => void;
  onMapClick?: (location: Coordinate) => void;
};

export default function GoogleSmartParkMap({
  userLocation,
  sourceName,
  parkingFacilities,
  selectedSpotId,
  onSelectSpot,
  onMapClick,
}: Props) {
  const elementRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapView | null>(null);
  const overlaysRef = useRef<Overlay[]>([]);
  const [maps, setMaps] = useState<MapsApi | null>(null);
  const [error, setError] = useState<string | null>(null);
  const selectedDestination = useNavigationStore((state) => state.selectedDestination);
  const selectedParking = useNavigationStore((state) => state.selectedParking);
  const status = useNavigationStore((state) => state.status);
  const route = useNavigationStore((state) =>
    state.status === 'walking' ? state.walkingRoute : state.drivingRoute,
  );

  useEffect(() => {
    let cancelled = false;
    void loadMaps().then((api) => {
      if (cancelled || !elementRef.current) return;
      mapRef.current = new api.Map(elementRef.current, {
        center: { lat: 24.8546842, lng: 67.0207055 },
        zoom: 13,
        mapTypeControl: false,
        streetViewControl: false,
      });
      setMaps(api);
    }).catch((cause: unknown) => {
      if (!cancelled) setError(cause instanceof Error ? cause.message : 'Map unavailable.');
    });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!maps || !mapRef.current || !onMapClick) return;
    const listener = mapRef.current.addListener('click', (event) => {
      if (event.latLng) {
        onMapClick({ latitude: event.latLng.lat(), longitude: event.latLng.lng() });
      }
    });
    return () => listener.remove();
  }, [maps, onMapClick]);

  useEffect(() => {
    if (!maps || !mapRef.current) return;
    const map = mapRef.current;
    for (const overlay of overlaysRef.current) overlay.setMap(null);
    overlaysRef.current = [];
    const addMarker = (location: Coordinate, label: string, title: string) => {
      const marker = new maps.Marker({ map, position: point(location), label, title });
      overlaysRef.current.push(marker);
      return marker;
    };
    const center = selectedDestination?.location ?? userLocation;
    if (center) map.setCenter(point(center));
    if (userLocation) addMarker(userLocation, sourceName === 'Your location' ? 'U' : 'S', sourceName ?? 'Starting location');
    if (selectedDestination) {
      addMarker(selectedDestination.location, 'D', selectedDestination.name);
    }
    if (selectedParking && !['parked', 'walking', 'arrived'].includes(status)) {
      addMarker(selectedParking.location, 'P', selectedParking.name ?? 'Selected parking');
    }
    for (const spot of parkingFacilities) {
      if (spot.id === selectedParking?.id) continue;
      const marker = addMarker(spot.location, spot.id === selectedSpotId ? 'S' : 'P', spot.name ?? 'Parking');
      marker.addListener('click', () => onSelectSpot(spot));
    }
    if (route?.geometry.coordinates.length) {
      const path = route.geometry.coordinates.map(([lng, lat]) => ({ lat, lng }));
      overlaysRef.current.push(new maps.Polyline({
        map,
        path,
        strokeColor: status === 'walking' ? '#198754' : '#2563eb',
        strokeWeight: 5,
      }));
      const bounds = new maps.LatLngBounds();
      for (const position of path) bounds.extend(position);
      map.fitBounds(bounds);
    }
    return () => {
      for (const overlay of overlaysRef.current) overlay.setMap(null);
      overlaysRef.current = [];
    };
  }, [maps, userLocation, sourceName, parkingFacilities, selectedSpotId, onSelectSpot, selectedDestination, selectedParking, status, route]);

  return (
    <div className="h-full w-full">
      <div ref={elementRef} className="h-full w-full" aria-label="Google map of destination and parking" />
      {error && <p role="alert" className="absolute bottom-4 left-4 rounded bg-white p-3 text-sm text-red-700">{error}</p>}
    </div>
  );
}

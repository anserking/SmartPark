import { useEffect } from 'react';
import {
  GeoJSON,
  MapContainer,
  Marker,
  Popup,
  TileLayer,
  useMap,
} from 'react-leaflet';
import type { Feature, LineString } from 'geojson';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

import { useNavigationStore } from '@/stores/navigationStore';
import type {
  Coordinate,
  ParkingRecommendation,
  RouteResult,
} from '@/types/smartpark';

const karachiCenter: Coordinate = {
  latitude: 24.8546842,
  longitude: 67.0207055,
};

const destinationIcon = L.divIcon({
  className: 'smartpark-marker-container',
  html: '<span class="smartpark-marker smartpark-marker--destination" aria-hidden="true">D</span>',
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const parkingIcon = L.divIcon({
  className: 'smartpark-marker-container',
  html: '<span class="smartpark-marker smartpark-marker--parking" aria-hidden="true">P</span>',
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const selectedParkingIcon = L.divIcon({
  className: 'smartpark-marker-container',
  html: '<span class="smartpark-marker smartpark-marker--selected-parking" aria-hidden="true">P</span>',
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});
const userIcon = L.divIcon({
  className: 'smartpark-marker-container',
  html: '<span class="smartpark-marker smartpark-marker--user" aria-hidden="true">U</span>',
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});

type SmartParkMapProps = {
  userLocation: Coordinate | null;
  parkingFacilities: ParkingRecommendation[];
  selectedSpotId: string | null;
  onSelectSpot: (spot: ParkingRecommendation) => void;
};

function MapCenter({ center }: { center: Coordinate }) {
  const map = useMap();

  useEffect(() => {
    map.setView([center.latitude, center.longitude], map.getZoom());
  }, [center.latitude, center.longitude, map]);

  return null;
}

function FitRoute({ route }: { route: RouteResult | null }) {
  const map = useMap();

  useEffect(() => {
    if (!route?.geometry.coordinates.length) return;
    const bounds = L.latLngBounds(
      route.geometry.coordinates.map(([longitude, latitude]) => [
        latitude,
        longitude,
      ]),
    );
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
  }, [map, route]);

  return null;
}

export default function SmartParkMap({
  userLocation,
  parkingFacilities,
  selectedSpotId,
  onSelectSpot,
}: SmartParkMapProps) {
  const selectedDestination = useNavigationStore(
    (state) => state.selectedDestination,
  );
  const selectedParking = useNavigationStore((state) => state.selectedParking);
  const status = useNavigationStore((state) => state.status);
  const drivingRoute = useNavigationStore((state) => state.drivingRoute);
  const walkingRoute = useNavigationStore((state) => state.walkingRoute);
  const center =
    selectedDestination?.location ?? userLocation ?? karachiCenter;
  const route = status === 'walking' ? walkingRoute : drivingRoute;
  const routeFeature: Feature<LineString> | null = route
    ? {
        type: 'Feature',
        properties: {},
        geometry: route.geometry,
      }
    : null;
  const selectedParkingVisible =
    selectedParking !== null &&
    status !== 'parked' &&
    status !== 'walking' &&
    status !== 'arrived';

  return (
    <div className="h-full w-full overflow-hidden">
      <MapContainer
        center={[center.latitude, center.longitude]}
        zoom={13}
        style={{ height: '100%', width: '100%' }}
      >
        <MapCenter center={center} />
        <FitRoute route={route} />
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />
        {userLocation && (
          <Marker
            position={[userLocation.latitude, userLocation.longitude]}
            icon={userIcon}
          >
            <Popup>Your location</Popup>
          </Marker>
        )}
        {selectedDestination && (
          <Marker
            position={[
              selectedDestination.location.latitude,
              selectedDestination.location.longitude,
            ]}
            icon={destinationIcon}
            opacity={status === 'driving' ? 0.45 : 1}
            zIndexOffset={status === 'driving' ? 0 : 1000}
          >
            <Popup>
              <strong>{selectedDestination.name}</strong>
              {selectedDestination.address && (
                <p>{selectedDestination.address}</p>
              )}
            </Popup>
          </Marker>
        )}
        {selectedParkingVisible && selectedParking && (
          <Marker
            position={[
              selectedParking.location.latitude,
              selectedParking.location.longitude,
            ]}
            icon={selectedParkingIcon}
          >
            <Popup>{selectedParking.name || 'Selected parking'}</Popup>
          </Marker>
        )}
        {parkingFacilities
          .filter((spot) => spot.id !== selectedParking?.id)
          .map((spot) => (
            <Marker
              key={spot.id}
              position={[spot.location.latitude, spot.location.longitude]}
              icon={spot.id === selectedSpotId ? selectedParkingIcon : parkingIcon}
              eventHandlers={{ click: () => onSelectSpot(spot) }}
            >
              <Popup>
                <div className="text-sm">
                  <p className="font-semibold">
                    {spot.parkingType.replace(/_/g, ' ')} parking
                  </p>
                  {spot.name && <p>{spot.name}</p>}
                  {spot.fee && <p>Fee: {spot.fee}</p>}
                  <p>
                    {(spot.destinationDistanceMeters / 1000).toFixed(1)} km
                    {' '}
                    {spot.destinationDistanceMethod === 'road'
                      ? 'by road to destination'
                      : 'straight-line to destination'}
                  </p>
                </div>
              </Popup>
            </Marker>
          ))}
        {routeFeature && route && (
          <GeoJSON
            key={`${status}-${route.distanceMeters}-${route.durationSeconds}`}
            data={routeFeature}
            style={{
              color: status === 'walking' ? '#198754' : '#2563eb',
              weight: 5,
              opacity: 0.9,
            }}
          />
        )}
      </MapContainer>
    </div>
  );
}

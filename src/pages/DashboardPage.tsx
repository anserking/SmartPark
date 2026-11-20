import { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useGeolocation } from '@/hooks/useGeolocation';
import { useNavigationStore } from '@/stores/navigationStore';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { AlertCircle, Car, Loader2, Navigation } from 'lucide-react';
import DestinationSearch from '@/components/DestinationSearch';
import SourceLocationSearch, { type SourceSelection } from '@/components/SourceLocationSearch';
import SmartParkMap from '@/components/GoogleSmartParkMap';
import { getParkingRecommendations } from '@/services/parkingRecommendations';
import { getRoute } from '@/services/routes';
import type {
  Coordinate,
  ParkingRecommendation,
  ParkingFacility,
  VehicleType,
} from '@/types/smartpark';

export default function DashboardPage() {
  const { position, isLoading: locationLoading, error: locationError } = useGeolocation();
  const [selectedSpot, setSelectedSpot] = useState<ParkingRecommendation | null>(null);
  const [sourceSelection, setSourceSelection] = useState<SourceSelection | null>(null);
  const [pickingSourceOnMap, setPickingSourceOnMap] = useState(false);
  const [navigationError, setNavigationError] = useState<string | null>(null);
  const [isRouting, setIsRouting] = useState(false);
  const routeRequest = useRef<AbortController | null>(null);
  const setCurrentLocation = useNavigationStore(
    (state) => state.setCurrentLocation,
  );
  const selectedDestination = useNavigationStore(
    (state) => state.selectedDestination,
  );
  const selectedParking = useNavigationStore((state) => state.selectedParking);
  const navigationStatus = useNavigationStore((state) => state.status);
  const vehicleType = useNavigationStore((state) => state.vehicleType);
  const drivingRoute = useNavigationStore((state) => state.drivingRoute);
  const walkingRoute = useNavigationStore((state) => state.walkingRoute);
  const selectParking = useNavigationStore((state) => state.selectParking);
  const selectVehicleType = useNavigationStore(
    (state) => state.selectVehicleType,
  );
  const startDriving = useNavigationStore((state) => state.startDriving);
  const confirmParking = useNavigationStore((state) => state.confirmParking);
  const startWalking = useNavigationStore((state) => state.startWalking);
  const completeJourney = useNavigationStore((state) => state.completeJourney);
  const clearDestination = useNavigationStore((state) => state.clearDestination);
  const sourceLocation = sourceSelection?.location ?? position;
  const searchBias = useMemo(
    () =>
      position
        ? { latitude: position.latitude, longitude: position.longitude }
        : undefined,
    [position?.latitude, position?.longitude],
  );
  useEffect(() => {
    setCurrentLocation(
      position
        ? { latitude: position.latitude, longitude: position.longitude }
        : null,
    );
  }, [position?.latitude, position?.longitude, setCurrentLocation]);

  useEffect(() => {
    routeRequest.current?.abort();
    routeRequest.current = null;
    setIsRouting(false);
    setNavigationError(null);
    setSelectedSpot(null);
  }, [selectedDestination?.id, vehicleType]);

  useEffect(
    () => () => {
      routeRequest.current?.abort();
    },
    [],
  );

  const nearbyCenter = selectedDestination?.location;
  const {
    data: spots,
    isLoading: spotsLoading,
    isError: spotsErrorOccurred,
    error: spotsError,
  } = useQuery({
    queryKey: [
      'parkingRecommendations',
      selectedDestination?.id,
      selectedDestination?.name,
      nearbyCenter?.latitude,
      nearbyCenter?.longitude,
      vehicleType,
      sourceLocation?.latitude,
      sourceLocation?.longitude,
    ],
    queryFn: ({ signal }) => {
      if (!nearbyCenter) return [];
      return getParkingRecommendations(
        nearbyCenter,
        selectedDestination?.name ?? '',
        vehicleType,
        sourceLocation,
        signal,
      );
    },
    enabled: !!selectedDestination && !!nearbyCenter,
  });

  const handleSelectSpot = (spot: ParkingRecommendation) => {
    if (navigationStatus !== 'idle' && navigationStatus !== 'destination_selected') {
      return;
    }
    setSelectedSpot(spot);
    setNavigationError(null);
    if (!selectedDestination || navigationStatus !== 'destination_selected') {
      return;
    }

    const facility: ParkingFacility = {
      id: spot.id,
      name: spot.name || `${spot.parkingType.replace(/_/g, ' ')} parking`,
      address: spot.address,
      location: {
        latitude: spot.location.latitude,
        longitude: spot.location.longitude,
      },
      parkingType: spot.parkingType,
      hourlyFee: spot.hourlyFee,
      supportsCar: spot.supportsCar,
      supportsBike: spot.supportsBike,
      availabilityStatus: spot.availabilityStatus,
      verificationStatus: spot.verificationStatus,
    };
    selectParking(facility);
  };

  const requestRoute = async (
    mode: VehicleType | 'walk',
    origin: { latitude: number; longitude: number },
    destination: { latitude: number; longitude: number },
    onSuccess: (route: Awaited<ReturnType<typeof getRoute>>) => void,
  ) => {
    const controller = new AbortController();
    routeRequest.current = controller;
    setIsRouting(true);
    setNavigationError(null);
    try {
      const route = await getRoute(mode, origin, destination, controller.signal);
      if (!controller.signal.aborted) {
        onSuccess(route);
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        setNavigationError(
          error instanceof Error ? error.message : 'Route request failed.',
        );
      }
    } finally {
      if (routeRequest.current === controller) {
        routeRequest.current = null;
        setIsRouting(false);
      }
    }
  };

  const handleStartDriving = () => {
    if (!sourceLocation || !selectedDestination || !selectedParking) {
      setNavigationError(
        'Select a destination, parking spot, and starting location to start driving.',
      );
      return;
    }
    const destinationId = selectedDestination.id;
    const origin = { latitude: sourceLocation.latitude, longitude: sourceLocation.longitude };
    const destination = selectedParking.location;
    void requestRoute(vehicleType, origin, destination, (route) => {
      if (
        useNavigationStore.getState().selectedDestination?.id === destinationId
      ) {
        startDriving(route);
      }
    });
  };

  const handleStartWalking = () => {
    if (!selectedDestination || !selectedParking) {
      setNavigationError('Select a destination and parking spot first.');
      return;
    }
    const destinationId = selectedDestination.id;
    void requestRoute(
      'walk',
      selectedParking.location,
      selectedDestination.location,
      (route) => {
        if (
          useNavigationStore.getState().selectedDestination?.id === destinationId
        ) {
          startWalking(route);
        }
      },
    );
  };

  const handleNavigationAction = (
    action: () => void,
  ) => {
    setNavigationError(null);
    try {
      action();
    } catch (error) {
      setNavigationError(
        error instanceof Error ? error.message : 'Navigation action failed.',
      );
    }
  };

  const handleResetJourney = () => {
    routeRequest.current?.abort();
    routeRequest.current = null;
    setIsRouting(false);
    setNavigationError(null);
    setSelectedSpot(null);
    setPickingSourceOnMap(false);
    clearDestination();
  };

  const routeSummary = (
    route: { distanceMeters: number; durationSeconds: number } | null,
  ) =>
    route
      ? `${(route.distanceMeters / 1000).toFixed(1)} km · ${Math.round(route.durationSeconds / 60)} min`
      : null;

  const journeyDescription = {
    idle: 'Search for a place to begin.',
    destination_selected: 'Choose a parking option, then start driving.',
    driving: 'Follow the route to your selected parking.',
    parked: 'Parking confirmed. Continue on foot.',
    walking: 'Follow the walking route to your destination.',
    arrived: 'You have arrived at your destination.',
  }[navigationStatus];

  return (
    <div className="relative h-full w-full overflow-hidden bg-[#e6e2d7]">
      <div className="absolute inset-0">
        <SmartParkMap
          userLocation={sourceLocation ?? null}
          parkingFacilities={spots ?? []}
          selectedSpotId={selectedSpot?.id ?? null}
          onSelectSpot={handleSelectSpot}
          sourceName={sourceSelection?.name ?? 'Your location'}
          onMapClick={pickingSourceOnMap && (navigationStatus === 'idle' || navigationStatus === 'destination_selected') ? (location: Coordinate) => {
            setSourceSelection({ name: 'Pinned location', location });
            setPickingSourceOnMap(false);
          } : undefined}
        />
      </div>

      <section
        aria-label="Destination search"
        className="absolute left-3 right-3 top-3 z-[1000] rounded-2xl border border-[#d8d0c0] bg-[#fffdf8] p-4 shadow-lg shadow-[#302914]/10 sm:left-4 sm:right-auto sm:top-4 sm:w-[min(100%-2rem,28rem)]"
      >
        <div className="mb-3 flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#7b6d59]">
              Karachi, Pakistan
            </p>
            <h1 className="mt-1 text-lg font-semibold tracking-tight text-[#273b2b]">
              Where are you going?
            </h1>
          </div>
          <span className="mt-1 grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[#e7e5d7] text-[#496348]">
            <Navigation aria-hidden="true" className="h-4 w-4" />
          </span>
        </div>
        <DestinationSearch bias={searchBias} />
        <SourceLocationSearch
          currentLocation={position ?? null}
          selected={sourceSelection}
          onSelect={(source) => { setSourceSelection(source); setPickingSourceOnMap(false); }}
          pickingOnMap={pickingSourceOnMap}
          onToggleMapPick={() => setPickingSourceOnMap((value) => !value)}
          disabled={navigationStatus !== 'idle' && navigationStatus !== 'destination_selected'}
        />
        {locationLoading && (
          <p role="status" className="mt-3 flex items-center gap-2 text-xs text-[#625d51]">
            <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
            Finding your location
          </p>
        )}
        {locationError && (
          <p role="alert" className="mt-3 flex items-center gap-2 text-xs text-[#8c2f24]">
            <AlertCircle aria-hidden="true" className="h-4 w-4 shrink-0" />
            Location is unavailable. Search still works without it.
          </p>
        )}
      </section>

      <aside
        aria-label="Journey and parking recommendations"
        className="absolute inset-x-0 bottom-0 z-[900] max-h-[53dvh] overflow-y-auto rounded-t-2xl border border-[#d8d0c0] bg-[#fffdf8]/95 p-3 shadow-[0_-8px_32px_rgba(48,41,20,0.12)] backdrop-blur-sm sm:inset-x-4 sm:bottom-4 sm:max-h-[48dvh] sm:rounded-2xl sm:p-4 lg:bottom-4 lg:left-4 lg:top-[20rem] lg:w-[25rem] lg:max-h-none"
      >
        <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-[#c8beaa] lg:hidden" />
        <div className="space-y-4">
          <Card className="border-[#d8d0c0] bg-transparent shadow-none">
            <CardHeader className="px-4 pb-2 pt-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <CardTitle className="text-base text-[#273b2b]">Your journey</CardTitle>
                  <CardDescription className="mt-1 leading-5 text-[#625d51]">
                    {journeyDescription}
                  </CardDescription>
                </div>
                <span className="rounded-full bg-[#e7e5d7] px-2.5 py-1 text-xs font-medium capitalize text-[#3d5942]">
                  {navigationStatus.replace('_', ' ')}
                </span>
              </div>
            </CardHeader>
            <CardContent className="space-y-3 px-4 pb-4">
              {navigationStatus === 'destination_selected' && (
                <>
                  <p className="line-clamp-2 text-sm font-medium text-[#273b2b]">
                    {selectedDestination?.name}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant={vehicleType === 'car' ? 'default' : 'outline'}
                      aria-pressed={vehicleType === 'car'}
                      className="min-h-11"
                      onClick={() => selectVehicleType('car')}
                    >
                      <Car aria-hidden="true" />
                      Car
                    </Button>
                    <Button
                      type="button"
                      variant={vehicleType === 'bike' ? 'default' : 'outline'}
                      aria-pressed={vehicleType === 'bike'}
                      className="min-h-11"
                      onClick={() => selectVehicleType('bike')}
                    >
                      Bike
                    </Button>
                  </div>
                  {selectedParking && (
                    <p className="text-sm text-[#625d51]">
                      Parking: {selectedParking.name || 'Selected parking'}
                    </p>
                  )}
                  {!sourceLocation && (
                    <p role="alert" className="text-sm text-[#8c2f24]">
                      Choose a starting location to start driving navigation.
                    </p>
                  )}
                  <Button
                    type="button"
                    className="min-h-11 w-full"
                    disabled={!sourceLocation || !selectedParking || isRouting}
                    onClick={handleStartDriving}
                  >
                    {isRouting ? 'Finding route…' : 'Start driving'}
                  </Button>
                </>
              )}
              {navigationStatus === 'driving' && (
                <>
                  {drivingRoute && (
                    <p className="text-sm font-medium text-[#273b2b]">
                      Driving · {routeSummary(drivingRoute)}
                    </p>
                  )}
                  <Button
                    type="button"
                    className="min-h-11 w-full"
                    onClick={() => handleNavigationAction(confirmParking)}
                  >
                    Confirm parking
                  </Button>
                </>
              )}
              {navigationStatus === 'parked' && (
                <>
                  <p className="text-sm text-[#625d51]">
                    Walk to {selectedDestination?.name}.
                  </p>
                  <Button
                    type="button"
                    className="min-h-11 w-full"
                    disabled={isRouting}
                    onClick={handleStartWalking}
                  >
                    {isRouting ? 'Finding walking route…' : 'Start walking'}
                  </Button>
                </>
              )}
              {navigationStatus === 'walking' && (
                <>
                  {walkingRoute && (
                    <p className="text-sm font-medium text-[#273b2b]">
                      Walking · {routeSummary(walkingRoute)}
                    </p>
                  )}
                  <Button
                    type="button"
                    className="min-h-11 w-full"
                    onClick={() => handleNavigationAction(completeJourney)}
                  >
                    I’ve arrived
                  </Button>
                </>
              )}
              {navigationStatus === 'arrived' && (
                <Button
                  type="button"
                  className="min-h-11 w-full"
                  onClick={handleResetJourney}
                >
                  Start a new journey
                </Button>
              )}
              {navigationStatus !== 'idle' && navigationStatus !== 'arrived' && (
                <Button
                  type="button"
                  variant="outline"
                  className="min-h-11 w-full"
                  disabled={isRouting}
                  onClick={handleResetJourney}
                >
                  Cancel journey
                </Button>
              )}
              {navigationError && (
                <p role="alert" className="text-sm text-[#8c2f24]">
                  {navigationError}
                </p>
              )}
            </CardContent>
          </Card>

          {selectedDestination && <section aria-labelledby="recommendations-heading" className="space-y-3">
            <div className="flex items-baseline justify-between gap-3 px-1">
              <h2 id="recommendations-heading" className="text-base font-semibold text-[#273b2b]">
                Parking near destination
              </h2>
              <span className="text-xs text-[#625d51]">
                {spots?.length ?? 0} options · within the closest search area
              </span>
            </div>
            {spotsLoading ? (
              <p role="status" className="flex items-center gap-2 px-1 py-3 text-sm text-[#625d51]">
                <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
                Finding parking nearby
              </p>
            ) : spotsErrorOccurred ? (
              <p role="alert" className="rounded-lg bg-[#f7e6e1] p-3 text-sm text-[#8c2f24]">
                Parking recommendations are unavailable
                {spotsError instanceof Error ? `: ${spotsError.message}` : '.'}
              </p>
            ) : spots && spots.length > 0 ? (
              <ul className="space-y-2">
                {spots.map((spot) => (
                  <li key={spot.id}>
                    <button
                      type="button"
                      aria-pressed={selectedSpot?.id === spot.id}
                      disabled={
                        navigationStatus !== 'idle' &&
                        navigationStatus !== 'destination_selected'
                      }
                      onClick={() => handleSelectSpot(spot)}
                      className={`w-full rounded-xl border p-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#496348] disabled:cursor-not-allowed disabled:opacity-60 ${
                        selectedSpot?.id === spot.id
                          ? 'border-[#496348] bg-[#edf0e7]'
                          : 'border-[#e2ddcf] bg-white hover:bg-[#f8f6f0]'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <span className="block truncate text-sm font-semibold text-[#273b2b]">
                            {spot.name || `${spot.parkingType.replace(/_/g, ' ')} parking`}
                          </span>
                          {spot.address && (
                            <span className="mt-1 block truncate text-xs text-[#625d51]">
                              {spot.address}
                            </span>
                          )}
                        </div>
                        <span className="shrink-0 rounded-full bg-[#f1eee5] px-2 py-1 text-[11px] text-[#625d51]">
                          {spot.source === 'google_maps' ? 'Google Maps' : spot.source === 'openstreetmap' ? 'OSM' : 'SmartPark'}
                        </span>
                      </div>
                      <span className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-[#625d51]">
                        <span>
                          {spot.destinationDistanceMeters >= 1000
                            ? `${(spot.destinationDistanceMeters / 1000).toFixed(1)} km`
                            : `${Math.round(spot.destinationDistanceMeters)} m`}{' '}
                          {spot.destinationDistanceMethod === 'road' ? 'by road' : 'straight-line'}
                        </span>
                        {spot.userDistanceMeters !== null && (
                          <span>{(spot.userDistanceMeters / 1000).toFixed(1)} km from you</span>
                        )}
                        {spot.fee && <span>{spot.fee}</span>}
                        <span>
                          {spot.verificationStatus === 'verified'
                            ? 'Verified'
                            : 'Not verified'}
                        </span>
                        {spot.availabilityStatus === 'unavailable' && (
                          <span>Unavailable</span>
                        )}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="rounded-lg bg-[#f1eee5] p-3 text-sm text-[#625d51]">
                No compatible parking facilities were found nearby.
              </p>
            )}
          </section>}
        </div>
      </aside>
    </div>
  );
}


// @ts-nocheck
import { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useGeolocation } from '@/hooks/useGeolocation';
import { useAuth } from '@/hooks/useAuth';
import { getActiveSessionForUser } from '@/services/parkingSessions';
import { useNavigationStore } from '@/stores/navigationStore';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { MapPin, Car, AlertCircle, Loader2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import DestinationSearch from '@/components/DestinationSearch';
import SmartParkMap from '@/components/SmartParkMap';
import { searchParkingFacilities } from '@/services/parking';
import { getRoute } from '@/services/routes';
import type {
  MapParkingFacility,
  ParkingFacility,
  VehicleType,
} from '@/types/smartpark';

export default function DashboardPage() {
  const { user } = useAuth();
  const { position, isLoading: locationLoading, error: locationError } = useGeolocation();
  const [selectedSpot, setSelectedSpot] = useState<MapParkingFacility | null>(null);
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
  const searchBias = useMemo(
    () =>
      position
        ? { latitude: position.latitude, longitude: position.longitude }
        : undefined,
    [position?.latitude, position?.longitude],
  );
  const destinationSearch = (
    <DestinationSearch bias={searchBias} />
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
  }, [selectedDestination?.id]);

  useEffect(
    () => () => {
      routeRequest.current?.abort();
    },
    [],
  );

  const nearbyCenter = selectedDestination?.location ?? position;
  const {
    data: spots,
    isLoading: spotsLoading,
    isError: spotsErrorOccurred,
    error: spotsError,
  } = useQuery({
    queryKey: [
      'nearbySpots',
      selectedDestination?.id,
      nearbyCenter?.latitude,
      nearbyCenter?.longitude,
    ],
    queryFn: () => {
      if (!nearbyCenter) return [];
      return searchParkingFacilities(nearbyCenter, 2000, 10);
    },
    enabled: !!nearbyCenter,
  });

  const { data: activeSession } = useQuery({
    queryKey: ['activeSession', user?.id],
    queryFn: () => {
      if (!user?.id) return null;
      return getActiveSessionForUser(user.id);
    },
    enabled: !!user?.id,
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  const handleSelectSpot = (spot: MapParkingFacility) => {
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
      name: spot.name || `${spot.parkingType.replaceAll('_', ' ')} parking`,
      address: spot.address,
      location: {
        latitude: spot.location.latitude,
        longitude: spot.location.longitude,
      },
      parkingType: spot.parkingType,
      hourlyFee: null,
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
    if (!position || !selectedDestination || !selectedParking) {
      setNavigationError(
        'Select a destination, parking spot, and allow location access to start driving.',
      );
      return;
    }
    const destinationId = selectedDestination.id;
    const origin = { latitude: position.latitude, longitude: position.longitude };
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
    clearDestination();
  };

  const routeSummary = (
    route: { distanceMeters: number; durationSeconds: number } | null,
  ) =>
    route
      ? `${(route.distanceMeters / 1000).toFixed(1)} km · ${Math.round(route.durationSeconds / 60)} min`
      : null;

  return (
    <div className="space-y-6">
      {destinationSearch}
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Search a destination to find parking near it.
        </p>
      </div>

      {locationLoading && (
        <p role="status" className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Getting your location. You can still search for a destination.
        </p>
      )}
      {locationError && (
        <p role="alert" className="flex items-center gap-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4" />
          Location is unavailable. Search remains available without location bias.
        </p>
      )}

      {activeSession && (
        <Card className="border-primary/50 bg-primary/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Car className="h-5 w-5" />
              Active Parking Session
            </CardTitle>
            <CardDescription>
              You have an active parking session
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">
                  Started {formatDistanceToNow(activeSession.startTime, { addSuffix: true })}
                </p>
              </div>
              <Link to="/sessions">
                <Button>View Session</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Map View</CardTitle>
              <CardDescription>
                {spotsLoading
                  ? 'Loading spots...'
                  : `${spots?.length || 0} mapped facilities ${selectedDestination ? 'near the destination' : 'near you'}`}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <SmartParkMap
                userLocation={position ?? null}
                parkingFacilities={spots ?? []}
                selectedSpotId={selectedSpot?.id ?? null}
                onSelectSpot={handleSelectSpot}
              />
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Journey</CardTitle>
              <CardDescription>
                {navigationStatus === 'idle' && 'Choose a destination and parking spot.'}
                {navigationStatus === 'destination_selected' && 'Ready to start driving.'}
                {navigationStatus === 'driving' && 'Drive to your selected parking spot.'}
                {navigationStatus === 'parked' && 'Parking confirmed. Continue on foot.'}
                {navigationStatus === 'walking' && 'Walk from parking to your destination.'}
                {navigationStatus === 'arrived' && 'You have arrived.'}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {navigationStatus === 'destination_selected' && (
                <>
                  <p className="text-sm">
                    Destination: {selectedDestination?.name}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      size="sm"
                      variant={vehicleType === 'car' ? 'default' : 'outline'}
                      aria-pressed={vehicleType === 'car'}
                      onClick={() => selectVehicleType('car')}
                    >
                      Car
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant={vehicleType === 'bike' ? 'default' : 'outline'}
                      aria-pressed={vehicleType === 'bike'}
                      onClick={() => selectVehicleType('bike')}
                    >
                      Bike
                    </Button>
                  </div>
                  {selectedParking && (
                    <p className="text-sm">
                      Parking: {selectedParking.name || 'Selected parking'}
                    </p>
                  )}
                  {!position && (
                    <p role="alert" className="text-sm text-destructive">
                      Allow location access to start driving navigation.
                    </p>
                  )}
                  <Button
                    type="button"
                    className="w-full"
                    disabled={!position || !selectedParking || isRouting}
                    onClick={handleStartDriving}
                  >
                    {isRouting ? 'Finding route…' : 'Start driving'}
                  </Button>
                </>
              )}
              {navigationStatus === 'driving' && (
                <>
                  {drivingRoute && (
                    <p className="text-sm">
                      Driving route: {routeSummary(drivingRoute)}
                    </p>
                  )}
                  <Button
                    type="button"
                    className="w-full"
                    onClick={() => handleNavigationAction(confirmParking)}
                  >
                    Confirm parking
                  </Button>
                </>
              )}
              {navigationStatus === 'parked' && (
                <>
                  <p className="text-sm">
                    Destination: {selectedDestination?.name}
                  </p>
                  <Button
                    type="button"
                    className="w-full"
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
                    <p className="text-sm">
                      Walking route: {routeSummary(walkingRoute)}
                    </p>
                  )}
                  <Button
                    type="button"
                    className="w-full"
                    onClick={() => handleNavigationAction(completeJourney)}
                  >
                    I’ve arrived
                  </Button>
                </>
              )}
              {navigationStatus === 'arrived' && (
                <Button
                  type="button"
                  className="w-full"
                  onClick={handleResetJourney}
                >
                  Start a new journey
                </Button>
              )}
              {navigationStatus !== 'idle' && navigationStatus !== 'arrived' && (
                <Button
                  type="button"
                  variant="outline"
                  className="w-full"
                  disabled={isRouting}
                  onClick={handleResetJourney}
                >
                  Cancel journey
                </Button>
              )}
              {navigationError && (
                <p role="alert" className="text-sm text-destructive">
                  {navigationError}
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>
                {selectedDestination ? 'Mapped parking near destination' : 'Nearby mapped parking'}
              </CardTitle>
              <CardDescription>
                {spotsLoading
                  ? 'Loading...'
                  : `${spots?.length || 0} OpenStreetMap facilities`}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {spotsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin" />
                </div>
              ) : spotsErrorOccurred ? (
                <p role="alert" className="text-sm text-destructive">
                  Could not load mapped parking
                  {spotsError instanceof Error ? `: ${spotsError.message}` : '.'}
                </p>
              ) : !nearbyCenter ? (
                <div className="text-center py-8 text-muted-foreground">
                  <MapPin className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Choose a destination or allow location access to find mapped parking.</p>
                </div>
              ) : spots && spots.length > 0 ? (
                <div className="space-y-3 max-h-[500px] overflow-y-auto">
                  {spots.map((spot) => (
                    <Card
                      key={spot.id}
                      className={`cursor-pointer transition-colors ${selectedSpot?.id === spot.id ? 'border-primary' : ''
                        }`}
                      onClick={() => handleSelectSpot(spot)}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between mb-2">
                          <Badge variant="outline" className="capitalize">
                            {spot.parkingType.replaceAll('_', ' ')}
                          </Badge>
                          <Badge variant="secondary" className="text-xs">
                            OpenStreetMap
                          </Badge>
                        </div>
                        <p className="text-sm font-medium mb-1">
                          {spot.name || 'Mapped parking'}
                        </p>
                        {spot.address && (
                          <p className="mb-2 text-xs text-muted-foreground">
                            {spot.address}
                          </p>
                        )}
                        <div className="flex items-center gap-4 text-xs text-muted-foreground">
                          <span>
                            {spot.straightLineDistanceMeters >= 1000
                              ? `${(spot.straightLineDistanceMeters / 1000).toFixed(1)} km`
                              : `${Math.round(spot.straightLineDistanceMeters)} m`}{' '}
                            straight-line
                          </span>
                          {spot.fee && <span>Fee: {spot.fee}</span>}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <MapPin className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No mapped parking facilities found nearby.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {selectedSpot && (
        <Card>
          <CardHeader>
            <CardTitle>Spot Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium mb-1">Type</p>
                <Badge className="capitalize">
                  {selectedSpot.parkingType.replaceAll('_', ' ')}
                </Badge>
              </div>
              <div>
                <p className="text-sm font-medium mb-1">Fee</p>
                <p>{selectedSpot.fee || 'Not specified'}</p>
              </div>
              <div>
                <p className="text-sm font-medium mb-1">Capacity</p>
                <p>{selectedSpot.capacity ?? 'Not specified'}</p>
              </div>
              <div>
                <p className="text-sm font-medium mb-1">Car access</p>
                <p>
                  {selectedSpot.supportsCar === null
                    ? 'Not specified'
                    : selectedSpot.supportsCar ? 'Yes' : 'No'}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium mb-1">Bike access</p>
                <p>
                  {selectedSpot.supportsBike === null
                    ? 'Not specified'
                    : selectedSpot.supportsBike ? 'Yes' : 'No'}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium mb-1">Distance</p>
                <p>
                  {(selectedSpot.straightLineDistanceMeters / 1000).toFixed(1)} km straight-line
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}


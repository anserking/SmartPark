import { beforeEach, describe, expect, it } from 'vitest';

import {
  NavigationTransitionError,
  useNavigationStore,
} from './navigationStore';
import type {
  Destination,
  ParkingFacility,
  RouteResult,
} from '@/types/smartpark';

const destination: Destination = {
  id: 'destination-1',
  name: 'Bahria University Karachi',
  category: 'university',
  address: 'Karachi',
  location: { latitude: 24.86, longitude: 67.03 },
};

const parking: ParkingFacility = {
  id: 'parking-1',
  name: 'Nearby parking',
  address: null,
  location: { latitude: 24.861, longitude: 67.031 },
  parkingType: 'parking',
  hourlyFee: null,
  supportsCar: null,
  supportsBike: null,
  availabilityStatus: 'unknown',
  verificationStatus: 'unverified',
};

const route: RouteResult = {
  geometry: {
    type: 'LineString',
    coordinates: [
      [67.03, 24.86],
      [67.031, 24.861],
    ],
  },
  distanceMeters: 100,
  durationSeconds: 120,
};

describe('navigation store', () => {
  beforeEach(() => {
    useNavigationStore.getState().resetNavigation();
  });

  it('transitions from driving to walking and retains parking as route origin', () => {
    const store = useNavigationStore.getState();
    store.selectDestination(destination);
    store.selectParking(parking);
    store.startDriving(route);
    store.confirmParking();
    store.startWalking(route);

    const walkingState = useNavigationStore.getState();
    expect(walkingState.status).toBe('walking');
    expect(walkingState.selectedParking).toEqual(parking);
    expect(walkingState.drivingRoute).toBeNull();
    expect(walkingState.walkingRoute).toEqual(route);

    walkingState.completeJourney();
    expect(useNavigationStore.getState().status).toBe('arrived');
  });

  it('rejects invalid transitions and clears journey data for a new destination', () => {
    const store = useNavigationStore.getState();
    expect(() => store.selectParking(parking)).toThrow(NavigationTransitionError);

    store.selectDestination(destination);
    store.selectParking(parking);
    store.startDriving(route);
    store.selectDestination({
      ...destination,
      id: 'destination-2',
      name: 'Saddar',
    });

    const resetState = useNavigationStore.getState();
    expect(resetState.status).toBe('destination_selected');
    expect(resetState.selectedParking).toBeNull();
    expect(resetState.drivingRoute).toBeNull();
    expect(resetState.walkingRoute).toBeNull();
  });
});

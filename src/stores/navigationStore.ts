import { create } from 'zustand';

import type {
  Coordinate,
  Destination,
  NavigationStatus,
  ParkingFacility,
  RouteResult,
  VehicleType,
} from '@/types/smartpark';

type NavigationData = {
  status: NavigationStatus;
  currentLocation: Coordinate | null;
  selectedDestination: Destination | null;
  selectedParking: ParkingFacility | null;
  vehicleType: VehicleType;
  drivingRoute: RouteResult | null;
  walkingRoute: RouteResult | null;
};

type NavigationActions = {
  setCurrentLocation: (location: Coordinate | null) => void;
  clearDestination: () => void;
  selectDestination: (destination: Destination) => void;
  selectParking: (parking: ParkingFacility) => void;
  selectVehicleType: (vehicleType: VehicleType) => void;
  startDriving: (route: RouteResult) => void;
  confirmParking: () => void;
  startWalking: (route: RouteResult) => void;
  completeJourney: () => void;
  resetNavigation: () => void;
};

export type NavigationState = NavigationData & NavigationActions;

export class NavigationTransitionError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NavigationTransitionError';
  }
}

function initialData(): NavigationData {
  return {
    status: 'idle',
    currentLocation: null,
    selectedDestination: null,
    selectedParking: null,
    vehicleType: 'car',
    drivingRoute: null,
    walkingRoute: null,
  };
}

export const useNavigationStore = create<NavigationState>((set, get) => ({
  ...initialData(),
  setCurrentLocation: (currentLocation) => set({ currentLocation }),
  clearDestination: () =>
    set((state) => ({
      status: 'idle',
      currentLocation: state.currentLocation,
      selectedDestination: null,
      selectedParking: null,
      vehicleType: state.vehicleType,
      drivingRoute: null,
      walkingRoute: null,
    })),
  selectDestination: (selectedDestination) =>
    set({
      status: 'destination_selected',
      selectedDestination,
      selectedParking: null,
      drivingRoute: null,
      walkingRoute: null,
    }),
  selectParking: (selectedParking) => {
    const state = get();
    if (state.status !== 'destination_selected' || !state.selectedDestination) {
      throw new NavigationTransitionError(
        'Select a destination before choosing parking',
      );
    }
    set({ selectedParking });
  },
  selectVehicleType: (vehicleType) => {
    const { status } = get();
    if (status !== 'idle' && status !== 'destination_selected') {
      throw new NavigationTransitionError(
        'Vehicle type cannot change after navigation starts',
      );
    }
    set({ vehicleType });
  },
  startDriving: (drivingRoute) => {
    const { status, selectedDestination, selectedParking } = get();
    if (
      status !== 'destination_selected' ||
      !selectedDestination ||
      !selectedParking
    ) {
      throw new NavigationTransitionError(
        'Select a destination and parking facility before driving',
      );
    }
    set({ status: 'driving', drivingRoute, walkingRoute: null });
  },
  confirmParking: () => {
    const { status, selectedParking } = get();
    if (status !== 'driving' || !selectedParking) {
      throw new NavigationTransitionError(
        'Parking can only be confirmed during driving navigation',
      );
    }
    set({ status: 'parked', drivingRoute: null, walkingRoute: null });
  },
  startWalking: (walkingRoute) => {
    const { status, selectedDestination, selectedParking } = get();
    if (status !== 'parked' || !selectedDestination || !selectedParking) {
      throw new NavigationTransitionError(
        'Confirm parking before starting walking navigation',
      );
    }
    set({ status: 'walking', walkingRoute });
  },
  completeJourney: () => {
    if (get().status !== 'walking') {
      throw new NavigationTransitionError(
        'A journey can only be completed during walking navigation',
      );
    }
    set({ status: 'arrived' });
  },
  resetNavigation: () => set(initialData()),
}));

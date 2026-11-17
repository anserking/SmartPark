export type Coordinate = {
  latitude: number;
  longitude: number;
};

export type VehicleType = 'car' | 'bike';

export type Destination = {
  id: string;
  name: string;
  category: string | null;
  address: string | null;
  location: Coordinate;
};

export type AvailabilityStatus =
  | 'verified'
  | 'unverified'
  | 'unavailable'
  | 'unknown';

export type ParkingFacility = {
  id: string;
  name: string | null;
  address: string | null;
  location: Coordinate;
  parkingType: string | null;
  hourlyFee: number | null;
  supportsCar: boolean | null;
  supportsBike: boolean | null;
  availabilityStatus: AvailabilityStatus;
  verificationStatus: 'verified' | 'unverified';
};

export type MapParkingFacility = {
  id: string;
  name: string | null;
  address: string | null;
  location: Coordinate;
  parkingType: string;
  fee: string | null;
  capacity: number | null;
  supportsCar: boolean | null;
  supportsBike: boolean | null;
  straightLineDistanceMeters: number;
  availabilityStatus: 'unknown';
  verificationStatus: 'unverified';
  source: 'openstreetmap';
};

export type RouteResult = {
  geometry: {
    type: 'LineString';
    coordinates: [number, number][];
  };
  distanceMeters: number;
  durationSeconds: number;
};

export type NavigationStatus =
  | 'idle'
  | 'destination_selected'
  | 'driving'
  | 'parked'
  | 'walking'
  | 'arrived';

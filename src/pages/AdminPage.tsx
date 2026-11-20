import { useState } from 'react';
import { KeyRound, Loader2, MapPin, Pencil, Plus, Trash2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  createAdminParkingSpot,
  deleteAdminParkingSpot,
  listAdminParkingSpots,
  updateAdminParkingSpot,
} from '@/services/adminParking';
import type {
  AdminParkingSpot,
  AvailabilityStatus,
} from '@/types/smartpark';

type FormValues = {
  name: string;
  address: string;
  latitude: string;
  longitude: string;
  parkingType: string;
  hourlyFee: string;
  capacity: string;
  availableSpaces: string;
  supportsCar: string;
  supportsBike: string;
};

const emptyForm: FormValues = {
  name: '',
  address: '',
  latitude: '',
  longitude: '',
  parkingType: 'parking',
  hourlyFee: '',
  capacity: '',
  availableSpaces: '',
  supportsCar: '',
  supportsBike: '',
};

const formForSpot = (spot: AdminParkingSpot): FormValues => ({
  name: spot.name ?? '',
  address: spot.address ?? '',
  latitude: String(spot.location.latitude),
  longitude: String(spot.location.longitude),
  parkingType: spot.parkingType ?? 'parking',
  hourlyFee: spot.hourlyFee === null ? '' : String(spot.hourlyFee),
  capacity: spot.capacity === null ? '' : String(spot.capacity),
  availableSpaces:
    spot.availableSpaces === null ? '' : String(spot.availableSpaces),
  supportsCar:
    spot.supportsCar === null ? '' : spot.supportsCar ? 'yes' : 'no',
  supportsBike:
    spot.supportsBike === null ? '' : spot.supportsBike ? 'yes' : 'no',
});

const parseNumber = (value: string): number | null =>
  value.trim() === '' ? null : Number(value);

const parseBoolean = (value: string): boolean | null =>
  value === 'yes' ? true : value === 'no' ? false : null;

const availabilityLabel: Record<AvailabilityStatus, string> = {
  verified: 'Verified',
  unverified: 'Not verified',
  unavailable: 'Unavailable',
  unknown: 'Availability unknown',
};

export default function AdminPage() {
  const [adminKey, setAdminKey] = useState('');
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [spots, setSpots] = useState<AdminParkingSpot[]>([]);
  const [form, setForm] = useState<FormValues>(emptyForm);
  const [editingSpotId, setEditingSpotId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadSpots = async (key: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const records = await listAdminParkingSpots(key);
      setSpots(records);
      setIsUnlocked(true);
      setAdminKey(key);
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : 'Could not load parking records.',
      );
      setIsUnlocked(false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUnlock = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await loadSpots(adminKey);
  };

  const handleFormChange = (field: keyof FormValues, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const handleResetForm = () => {
    setForm(emptyForm);
    setEditingSpotId(null);
  };

  const handleSubmitSpot = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setNotice(null);

    const latitude = parseNumber(form.latitude);
    const longitude = parseNumber(form.longitude);
    const hourlyFee = parseNumber(form.hourlyFee);
    const capacity = parseNumber(form.capacity);
    const availableSpaces = parseNumber(form.availableSpaces);
    if (
      latitude === null ||
      longitude === null ||
      !Number.isFinite(latitude) ||
      !Number.isFinite(longitude) ||
      latitude < -90 ||
      latitude > 90 ||
      longitude < -180 ||
      longitude > 180
    ) {
      setError('Enter a valid latitude and longitude for the parking location.');
      return;
    }
    if (hourlyFee !== null && (!Number.isFinite(hourlyFee) || hourlyFee < 0)) {
      setError('Hourly fee must be a non-negative number.');
      return;
    }
    if (
      capacity !== null &&
      (!Number.isInteger(capacity) || capacity < 0)
    ) {
      setError('Capacity must be a non-negative whole number.');
      return;
    }
    if (
      availableSpaces !== null &&
      (!Number.isInteger(availableSpaces) ||
        availableSpaces < 0 ||
        (capacity !== null && availableSpaces > capacity))
    ) {
      setError('Available spaces must be a non-negative whole number no greater than capacity.');
      return;
    }

    const editablePayload = {
      name: form.name.trim() || null,
      address: form.address.trim() || null,
      location: { latitude, longitude },
      parkingType: form.parkingType.trim() || null,
      hourlyFee,
      supportsCar: parseBoolean(form.supportsCar),
      supportsBike: parseBoolean(form.supportsBike),
      capacity,
      availableSpaces,
    };
    const createPayload = {
      ...editablePayload,
      availabilityStatus: 'unknown' as const,
      verificationStatus: 'unverified' as const,
    };

    setIsSaving(true);
    try {
      if (editingSpotId) {
        await updateAdminParkingSpot(adminKey, editingSpotId, editablePayload);
        setNotice('Parking record updated.');
      } else {
        await createAdminParkingSpot(adminKey, createPayload);
        setNotice('Parking record added.');
      }
      handleResetForm();
      await loadSpots(adminKey);
    } catch (saveError) {
      setError(
        saveError instanceof Error
          ? saveError.message
          : 'Could not save this parking record.',
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleVerification = async (
    spot: AdminParkingSpot,
    availabilityStatus: 'verified' | 'unavailable',
  ) => {
    setError(null);
    setNotice(null);
    try {
      await updateAdminParkingSpot(adminKey, spot.id, {
        availabilityStatus,
        ...(availabilityStatus === 'verified'
          ? { verificationStatus: 'verified' }
          : {}),
      });
      setNotice(
        availabilityStatus === 'verified'
          ? 'Parking record verified.'
          : 'Parking record marked unavailable.',
      );
      await loadSpots(adminKey);
    } catch (updateError) {
      setError(
        updateError instanceof Error
          ? updateError.message
          : 'Could not update this parking record.',
      );
    }
  };

  const handleDelete = async (spot: AdminParkingSpot) => {
    if (!window.confirm(`Delete ${spot.name || 'this parking record'}?`)) {
      return;
    }
    setError(null);
    setNotice(null);
    try {
      await deleteAdminParkingSpot(adminKey, spot.id);
      setSpots((current) => current.filter((item) => item.id !== spot.id));
      if (editingSpotId === spot.id) handleResetForm();
      setNotice('Parking record deleted.');
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : 'Could not delete this parking record.',
      );
    }
  };

  const handleLock = () => {
    setAdminKey('');
    setIsUnlocked(false);
    setSpots([]);
    setError(null);
    setNotice(null);
    handleResetForm();
  };

  return (
    <main className="min-h-screen bg-[#f4f0e7] px-4 py-8 text-[#242a22] sm:px-8">
      <div className="mx-auto max-w-5xl space-y-8">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#7b6d59]">
              SmartPark operations
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
              Parking administration
            </h1>
            <p className="mt-2 max-w-[65ch] text-sm leading-6 text-[#625d51]">
              Keep location details and verification status current for drivers.
            </p>
          </div>
          {isUnlocked && (
            <Button type="button" variant="outline" onClick={handleLock}>
              Lock administration
            </Button>
          )}
        </header>

        {!isUnlocked ? (
          <form
            onSubmit={handleUnlock}
            className="max-w-xl space-y-4 rounded-xl border border-[#d8d0c0] bg-[#fffdf8] p-5"
          >
            <div className="flex items-center gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-full bg-[#e7e5d7] text-[#3d5942]">
                <KeyRound aria-hidden="true" className="h-5 w-5" />
              </span>
              <div>
                <h2 className="font-semibold">Admin key required</h2>
                <p className="text-sm text-[#625d51]">
                  The key is held only in this page and is not saved.
                </p>
              </div>
            </div>
            <label htmlFor="admin-key" className="block text-sm font-medium">
              Server admin key
            </label>
            <Input
              id="admin-key"
              type="password"
              autoComplete="current-password"
              value={adminKey}
              onChange={(event) => setAdminKey(event.target.value)}
              className="h-11 bg-white"
              required
            />
            <Button type="submit" className="min-h-11" disabled={isLoading}>
              {isLoading ? (
                <>
                  <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
                  Checking key
                </>
              ) : (
                'Unlock'
              )}
            </Button>
          </form>
        ) : (
          <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,0.8fr)]">
            <section aria-labelledby="parking-records-heading" className="space-y-4">
              <div className="flex items-baseline justify-between gap-3">
                <h2 id="parking-records-heading" className="text-xl font-semibold">
                  Parking records
                </h2>
                <span className="text-sm text-[#625d51]">
                  {spots.length} {spots.length === 1 ? 'record' : 'records'}
                </span>
              </div>
              {isLoading ? (
                <p role="status" className="flex items-center gap-2 text-sm text-[#625d51]">
                  <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
                  Loading records
                </p>
              ) : spots.length === 0 ? (
                <div className="rounded-xl border border-dashed border-[#c8beaa] p-6 text-sm text-[#625d51]">
                  No records yet. Add the first verified parking location.
                </div>
              ) : (
                <ul className="space-y-3">
                  {spots.map((spot) => (
                    <li
                      key={spot.id}
                      className="space-y-4 rounded-xl border border-[#d8d0c0] bg-[#fffdf8] p-4"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0">
                          <h3 className="font-semibold">
                            {spot.name || 'Unnamed parking'}
                          </h3>
                          <p className="mt-1 flex items-start gap-1.5 text-sm text-[#625d51]">
                            <MapPin aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
                            <span>
                              {spot.address || 'Address not specified'}
                              <span className="block text-xs">
                                {spot.location.latitude.toFixed(5)},{' '}
                                {spot.location.longitude.toFixed(5)}
                              </span>
                            </span>
                          </p>
                        </div>
                        <span className="rounded-full bg-[#e7e5d7] px-3 py-1 text-xs font-medium text-[#3d5942]">
                          {availabilityLabel[spot.availabilityStatus]}
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          className="min-h-11"
                          onClick={() => {
                            setEditingSpotId(spot.id);
                            setForm(formForSpot(spot));
                          }}
                        >
                          <Pencil aria-hidden="true" />
                          Edit
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          className="min-h-11"
                          onClick={() => void handleVerification(spot, 'verified')}
                        >
                          Verify
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          className="min-h-11"
                          onClick={() => void handleVerification(spot, 'unavailable')}
                        >
                          Mark unavailable
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="destructive"
                          className="min-h-11"
                          onClick={() => void handleDelete(spot)}
                        >
                          <Trash2 aria-hidden="true" />
                          Delete
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section aria-labelledby="edit-record-heading">
              <form
                onSubmit={handleSubmitSpot}
                className="space-y-4 rounded-xl border border-[#d8d0c0] bg-[#fffdf8] p-5"
              >
                <div className="flex items-center gap-2">
                  {editingSpotId ? (
                    <Pencil aria-hidden="true" className="h-4 w-4 text-[#496348]" />
                  ) : (
                    <Plus aria-hidden="true" className="h-5 w-5 text-[#496348]" />
                  )}
                  <h2 id="edit-record-heading" className="text-lg font-semibold">
                    {editingSpotId ? 'Edit parking' : 'Add parking'}
                  </h2>
                </div>
                <Field label="Name">
                  <Input
                    value={form.name}
                    onChange={(event) => handleFormChange('name', event.target.value)}
                    maxLength={255}
                    className="bg-white"
                  />
                </Field>
                <Field label="Address">
                  <Input
                    value={form.address}
                    onChange={(event) => handleFormChange('address', event.target.value)}
                    maxLength={500}
                    className="bg-white"
                  />
                </Field>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Latitude">
                    <Input
                      inputMode="decimal"
                      value={form.latitude}
                      onChange={(event) => handleFormChange('latitude', event.target.value)}
                      className="bg-white"
                      required
                    />
                  </Field>
                  <Field label="Longitude">
                    <Input
                      inputMode="decimal"
                      value={form.longitude}
                      onChange={(event) => handleFormChange('longitude', event.target.value)}
                      className="bg-white"
                      required
                    />
                  </Field>
                </div>
                <Field label="Parking type">
                  <Input
                    value={form.parkingType}
                    onChange={(event) => handleFormChange('parkingType', event.target.value)}
                    maxLength={80}
                    className="bg-white"
                  />
                </Field>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Hourly fee (PKR)">
                    <Input
                      type="number"
                      min="0"
                      step="0.01"
                      value={form.hourlyFee}
                      onChange={(event) => handleFormChange('hourlyFee', event.target.value)}
                      className="bg-white"
                    />
                  </Field>
                  <Field label="Capacity">
                    <Input
                      type="number"
                      min="0"
                      step="1"
                      value={form.capacity}
                      onChange={(event) => handleFormChange('capacity', event.target.value)}
                      className="bg-white"
                    />
                  </Field>
                </div>
                <Field label="Available spaces">
                  <Input
                    type="number"
                    min="0"
                    step="1"
                    value={form.availableSpaces}
                    onChange={(event) =>
                      handleFormChange('availableSpaces', event.target.value)
                    }
                    className="bg-white"
                  />
                </Field>
                <div className="grid grid-cols-2 gap-3">
                  <SelectField
                    label="Car access"
                    value={form.supportsCar}
                    onChange={(value) => handleFormChange('supportsCar', value)}
                  />
                  <SelectField
                    label="Bike access"
                    value={form.supportsBike}
                    onChange={(value) => handleFormChange('supportsBike', value)}
                  />
                </div>
                <div className="flex flex-wrap gap-2 pt-1">
                  <Button type="submit" className="min-h-11" disabled={isSaving}>
                    {isSaving ? 'Saving' : editingSpotId ? 'Save changes' : 'Add parking'}
                  </Button>
                  {editingSpotId && (
                    <Button type="button" variant="outline" onClick={handleResetForm}>
                      Cancel edit
                    </Button>
                  )}
                </div>
              </form>
            </section>
          </div>
        )}

        {error && (
          <p role="alert" className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-900">
            {error}
          </p>
        )}
        {notice && (
          <p role="status" className="rounded-lg border border-[#b8c5a6] bg-[#e9eddf] px-4 py-3 text-sm text-[#334b35]">
            {notice}
          </p>
        )}
      </div>
    </main>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block space-y-1.5 text-sm font-medium">
      {label}
      {children}
    </label>
  );
}

function SelectField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block space-y-1.5 text-sm font-medium">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-11 w-full rounded-md border border-input bg-white px-3 text-base outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <option value="">Unknown</option>
        <option value="yes">Yes</option>
        <option value="no">No</option>
      </select>
    </label>
  );
}

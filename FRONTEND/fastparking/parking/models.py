from datetime import datetime
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.db.models import Sum, JSONField
from django.conf import settings


from .services import compare_plates
from photos.models import Photo
from cars.models import Car


class ParkingSpace(models.Model):
    number = models.CharField(max_length=10, unique=True)
    status = models.BooleanField(default=False, help_text="False is free")  # False - вільно, True - зайнято
    car_num = models.CharField(max_length=16, blank=True, null=True)
    description = models.CharField(max_length=64, blank=True, null=True)
    category = models.SmallIntegerField(blank=True, null=True, help_text="The smallest number is filled in first")

    def __str__(self):
        return self.number


class Registration(models.Model):
    parking = models.ForeignKey(ParkingSpace, on_delete=models.CASCADE)
    entry_datetime = models.DateTimeField(default=timezone.now)
    car_number_in = models.CharField(max_length=16)
    # tariff_in = models.DecimalField(
    #     max_digits=10, decimal_places=2, null=True, blank=True
    # )
    tariff_in: JSONField = models.JSONField(null=True, blank=True)
    exit_datetime = models.DateTimeField(null=True, blank=True)
    invoice = models.CharField(max_length=255, null=True, blank=True)
    car_number_out = models.CharField(max_length=16, null=True, blank=True)
    photo_in = models.ForeignKey(
        Photo,
        on_delete=models.SET_NULL,
        related_name="registration_photo_in",
        null=True,
        blank=True,
    )
    photo_out = models.ForeignKey(
        Photo,
        on_delete=models.SET_NULL,
        related_name="registration_photo_out",
        null=True,
        blank=True,
    )
    car = models.ForeignKey(Car, on_delete=models.SET_NULL, null=True, blank=True)

    def round_to_int__(self, number):
        """Rounds a number to the nearest integer, using ceiling for positive values
        and floor for negative values.

        Args:
            number: The number to round.

        Returns:
            The rounded integer.
        """
        return int(round(number + (0.5 if number > 0 else -0.5)))

        # # Test cases
        # rounded_1 = round_to_int(1.01)
        # rounded_2 = round_to_int(0.9)

        # print(rounded_1)  # Output: 2
        # print(rounded_2)  # Output: 1

    def is_pay_pass(self) -> bool | None:
        car = self.car
        if car:
            return car.PayPass

    def calculate_fee_from_duration(self, hours: float) -> float | None:
        price_per_day = float(self.tariff_in["d"]) if self.tariff_in.get("d") else None
        price_per_hour = float(self.tariff_in["h"]) if self.tariff_in.get("h") else None
        if price_per_day and price_per_hour:
            days = hours // 24
            hours_of_day = hours % 24
            parking_fee = round(price_per_day * days + price_per_hour * hours_of_day, 2)
            # print(f"D+H: {hours=}, {days=}, {hours_of_day=}")
        elif price_per_hour:
            parking_fee = round(price_per_hour * hours, 2)
            # print(f"H: {hours=}")
        elif price_per_day:
            parking_fee = round(price_per_day * hours / 24.0, 1)
            # print(f"D: {hours / 24.0=}")
        else:
            parking_fee = None
        # print(f"*** {parking_fee=}, {price_per_day=}, {price_per_hour=}")
        return parking_fee

    def calculate_parking_fee(self) -> float | None:
        # print(
        #     f"Calculating parking fee... tariff: {self.tariff_in}",
        # )
        # PayPass - free all time
        if self.is_pay_pass():
            return 0.0  # Free for pay pass

        current_time = timezone.now()

        if self.exit_datetime:
            # Fix time for exit cars
            current_time = self.exit_datetime
        else:
            # Froze TIME during 15 min after last pay.
            time_delta = timezone.timedelta(minutes=15)
            last_payment = self.get_last_payment()
            # Calculate the threshold time (15 minutes ago)
            acceptable_time = current_time - time_delta
            if last_payment and last_payment > acceptable_time:
                current_time = last_payment
            # print(f"{last_payment=}, {current_time=}")

        # calculate duration
        if self.entry_datetime:
            duration = current_time - self.entry_datetime
            hours = duration.total_seconds() / 3600  # переводимо час в години

            #  Free first 15 mins
            if hours < 0.25:
                hours = 0  # Free first 15 mins
            else:
                hours = self.round_to_int__(hours)
            # get price_from_hour
            return self.calculate_fee_from_duration(hours)
        return None

    def get_current_duration(self) -> float | None:
        current_time = timezone.now()
        if self.entry_datetime:
            duration = current_time - self.entry_datetime
            hours = duration.total_seconds() / 3600  # in hours
            return hours

    def get_duration(self) -> float | None:
        if self.entry_datetime and self.exit_datetime:
            duration = self.exit_datetime - self.entry_datetime
            if isinstance(duration, timezone.timedelta):
                hours = duration.total_seconds() / 3600  # in hours
                return hours
        else:
            return self.get_current_duration()

    def compare_in_out(self):
        return compare_plates(self.car_number_in, self.car_number_out)

    def calculate_total_payed(self) -> Decimal | None:
        total_amount = self.payment_set.aggregate(total=Sum("amount")).get("total")
        return total_amount

    def get_last_payment(self) -> datetime | None:
        last_payment = self.payment_set.order_by("-datetime").first()
        if last_payment:
            return last_payment.datetime
        else:
            return None

    def __str__(self):
        if self.invoice:
            invoice_predict = self.invoice
        else:
            invoice_predict = self.calculate_parking_fee()
        currency = settings.PAYMENT_CURRENCY[1]
        if invoice_predict:
            invoice_predict = f"{float(invoice_predict):.2f} {currency}"
        total_amount = self.calculate_total_payed()
        total_amount_formatted = ""
        if total_amount:
            total_amount_formatted = f" - Payed: {float(total_amount):.2f} {currency}"
        e_date = self.entry_datetime.strftime("%Y-%m-%d %H:%M")
        result = f"Reg. ID: {self.pk:06} - Car NO: {self.car_number_in} - Parking: {self.parking.number} - Entry: {e_date} - Invoice*: {invoice_predict}{total_amount_formatted}"

        return result

FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY customer-service/ customer-service/
COPY database/customers.sql database/customers.sql
COPY frontend/src/validation/vehicle-identifiers.json frontend/src/validation/vehicle-identifiers.json
COPY tests/vehicle-identifiers.cases.json tests/vehicle-identifiers.cases.json
RUN dotnet publish customer-service/CustomerService.csproj -c Release -o /out

FROM mcr.microsoft.com/dotnet/aspnet:10.0
WORKDIR /app
COPY --from=build /out/ .
ENTRYPOINT ["dotnet", "CustomerService.dll"]

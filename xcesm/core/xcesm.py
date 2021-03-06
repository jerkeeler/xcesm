#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 13 22:17:01 2017

@author: Yefee
"""

from __future__ import absolute_import

import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
from . import utils as utl
from ..config import cesmconstant as cc
from ..plots import colormap as clrmp

@xr.register_dataset_accessor('cam')
class CAMDiagnosis(object):
    def __init__(self, xarray_obj):
        self._obj = xarray_obj


    # precipation
    def precp(self):
        try:
            precc = self._obj.PRECC
            precl = self._obj.PRECL
            if precc.max() > 1:
                precp = precc + precl
            else:
                precp = (precc + precl) * cc.sday * cc.rhofw # convert to mm/day
            precp.name = 'precp'
            precp.attrs['Description'] = 'Precipitation in CAM.'
            precp.attrs['units'] = 'mm/day'
        except:
            raise ValueError('object has no PRECC.')

        return precp

    # d18op
    @property
    def d18op(self):
        '''
        compute d18O precp
        '''
        try:
            p16 = self._obj.PRECRC_H216Or + self._obj.PRECSC_H216Os + \
            self._obj.PRECRL_H216OR + self._obj.PRECSL_H216OS

            p18 = self._obj.PRECRC_H218Or + self._obj.PRECSC_H218Os + \
            self._obj.PRECRL_H218OR + self._obj.PRECSL_H218OS

#            p16.values[p16.values < 1e-50] = np.nan
            d18op = (p18 / p16 - 1)*1000
            d18op.name = 'd18Op'
        except:
            raise ValueError('object has no PRECRC_H216Or.')
        return d18op

    # d18ov
    @property
    def d18ov(self):
        '''
        compute d18O precp
        '''
        try:
            p16 = self._obj.H216OV

            p18 = self._obj.H218OV 

#            p16.values[p16.values < 1e-50] = np.nan
            d18ov = (p18 / p16 - 1)*1000
            d18ov.name = 'd18Ov'
        except:
            raise ValueError('object has no H216OV.')
        return d18ov

    # dDp
    @property
    def dDp(self):
        '''
        compute d18O precp
        '''
        try:
            p16 = self._obj.PRECRC_H216Or + self._obj.PRECSC_H216Os + \
            self._obj.PRECRL_H216OR + self._obj.PRECSL_H216OS

            pD = self._obj.PRECRC_HDOr + self._obj.PRECSC_HDOs + \
            self._obj.PRECRL_HDOR + self._obj.PRECSL_HDOS

            p16.values[p16.values < 1e-50] = np.nan
            dDp = (pD / p16 - 1)*1000
            dDp.name = 'dDp'
        except:
            raise ValueError('object has no PRECRC_H216Or.')
        return dDp

    def compute_heat_transport(self, dsarray, method):

        from scipy import integrate
        '''
        compute heat transport using surface(toa,sfc) flux
        '''
        lat_rad = np.deg2rad(dsarray.lat)
        coslat = np.cos(lat_rad)
        field = coslat * dsarray

        if method is "Flux_adjusted":
            field = field - field.mean("lat")
            print("The heat transport is computed by Flux adjestment.")
        elif method is "Flux":
            print("The heat transport is computed by Flux.")
        elif method is "Dynamic":
            print("The heat transport is computed by dynamic method.")
            raise ValueError("Dynamic method has not been implimented.")
        else:
            raise ValueError("Method is not supported.")


        try:
            latax = field.get_axis_num('lat')
        except:
            raise ValueError('No lat coordinate!')

        integral = integrate.cumtrapz(field, x=lat_rad, initial=0., axis=latax)


        transport = 1e-15 * 2 * np.math.pi * integral * cc.rearth **2  # unit in PW

        if isinstance(field, xr.DataArray):
            result = field.copy()
            result.values = transport
        return result.T

    # heat transport
#    @property
    def planet_heat_transport(self, method="Flux"):

        '''
        compute heat transport using surface(toa,sfc) flux
        '''

        OLR = self._obj.FLNT.mean('lon')
        ASR = self._obj.FSNT.mean('lon')
        Rtoa = ASR - OLR  # net downwelling radiation

        try:
            # this block use atm flux to infer ocean heat trnasport but, use ocn output shall be more accurate
            # make sea mask from landfrac and icefrac
            lnd = self._obj.LANDFRAC
            ice = self._obj.ICEFRAC
            mask = 1- (lnd + ice) * 0.5
            LHF = self._obj.LHFLX * mask
            LHF = LHF.mean('lon')
            SHF = self._obj.SHFLX * mask
            SHF = SHF.mean('lon')

            LWsfc = self._obj.FLNS * mask
            LWsfc = LWsfc.mean('lon')
            SWsfc = -self._obj.FSNS * mask
            SWsfc = SWsfc.mean('lon')

            SurfaceRadiation = LWsfc + SWsfc  # net upward radiation from surface
        #        SurfaceHeatFlux = SurfaceRadiation + LHF + SHF + SnowFlux  # net upward surface heat flux
            SurfaceHeatFlux = SurfaceRadiation + LHF + SHF  # net upward surface heat flux
            Fatmin = Rtoa + SurfaceHeatFlux  # net heat flux in to atmosphere

            AHT = self.compute_heat_transport(Fatmin, method)
            PHT = self.compute_heat_transport(Rtoa, method)
            OHT = PHT - AHT
        except:
            PHT = self.compute_heat_transport(Rtoa, method)
            AHT = None
            OHT = None


#        return PHT, AHT, OHT
        return PHT, AHT, OHT


    def net_heat_flux(self):
        
        OLR = self._obj.FLNT
        ASR = self._obj.FSNT
        Rtoa = ASR - OLR  # net downwelling radiation

        LHF = self._obj.LHFLX 
        LHF = LHF
        SHF = self._obj.SHFLX 
        SHF = SHF

        LWsfc = self._obj.FLNS 
        LWsfc = LWsfc
        SWsfc = -self._obj.FSNS 
        SWsfc = SWsfc

        SurfaceRadiation = LWsfc + SWsfc  + SHF + LHF# net upward radiation from surface

        NHeat = Rtoa + SurfaceRadiation

        return NHeat

    def mse(self):
        Q = self._obj.Q
        T = self._obj['T']
        Z3 = self._obj.Z3
        
        if Q.max() > 1:
            Q = Q * 1e-3 # convert to kg/kg
        
        if T.max() < 200:
            T = T + cc.tkfrz

        MSE = cc.cpdair * T + cc.latvap * Q + cc.g * Z3
        MSE.attrs['unit'] = 'J/kg'
        return MSE

@xr.register_dataset_accessor('pop')
class POPDiagnosis(object):
    def __init__(self, xarray_obj):
        self._obj = xarray_obj

    # PA/TH
    def comp_path(self):
        kmt = xcesm.core.utils.kmt_cube_g16
        pa = self._obj.PA_P * kmt
        pa = pa.sum('z_t')

        th = self._obj.TH_P * kmt
        th = th.sum('z_t')
        path = pa / th
        path = path * tarea
        path = path.groupby('time').sum() / tarea.utils.North_Atlantic().sum()
        return path.load()


    # PA/TH local
    def pa_th(self, lat, lon, depth):
        
        dsarray = self._obj
        
        if lon < 0:
            lon = lon + 360   # west hemisphere is negative 

        area = (dsarray.TLAT>lat-0.5) & (dsarray.TLAT<lat+0.5) \
                & (dsarray.TLONG>lon-0.5) & (dsarray.TLONG<lon+0.5)
        
        pa = dsarray.PA_P.where(area, drop=True)
        th = dsarray.TH_P.where(area, drop=True)

        pa = pa.mean('nlon').mean('nlat').dropna('z_t').load()
        th = th.mean('nlon').mean('nlat').dropna('z_t').load()

        if dsarray.z_t[-1] > 1e5:
            pa = pa.sel(z_t=depth * 1e2, method='nearest')
            th = th.sel(z_t=depth * 1e2, method='nearest')
        else:
            pa = pa.sel(z_t=depth, method='nearest')
            th = th.sel(z_t=depth, method='nearest')
        path = pa / th
        return path.load()


    # amoc
    def amoc(self, method='index', depth=500, lats=[30,80]):
        if method == 'index':
            try:
                if 'MOC' in list(self._obj.keys()):
                    moc = self._obj.MOC.isel(transport_reg=1,moc_comp=0).copy()
                    moc.values[np.abs(moc.values) < 1e-6] = np.nan
                    # amoc area
                    if moc.moc_z[-1] > 1e5:
                        z_bound = moc.moc_z[(moc.moc_z > depth * 1e2) & (moc.moc_z < 5e5)] #cm
                    else:
                        z_bound = moc.moc_z[(moc.moc_z > depth) & (moc.moc_z < 5e3)] #m
                    lat_bound = moc.lat_aux_grid[
                                (moc.lat_aux_grid > lats[0]) & (moc.lat_aux_grid < lats[1])]
                    if "time" in moc.dims:
                        amoc = moc.sel(moc_z=z_bound, lat_aux_grid=lat_bound).groupby('time').max()
                    else:
                        amoc = moc.sel(moc_z=z_bound, lat_aux_grid=lat_bound).max()

                elif 'amoc' in list(self._obj.keys()):
                    moc = self._obj.amoc
                    moc.values[np.abs(moc.values) < 1e-6] = np.nan
                    # amoc area
                    if moc.z_t[-1] > 1e5:
                        z_bound = moc.z_t[(moc.z_t > depth * 1e2) & (moc.z_t < 5e5)] #cm
                    else:
                        z_bound = moc.z_t[(moc.z_t > depth) & (moc.z_t < 5e3)] #m
                    lat_bound = moc.lat[
                                (moc.lat > lats[0]) & (moc.lat < lats[1])]
                    if "time" in moc.dims:
                        amoc = moc.sel(z_t=z_bound, lat=lat_bound).groupby('time').max()
                    else:
                        amoc = moc.sel(z_t=z_bound, lat=lat_bound).max()
            except:
                raise ValueError('object has no MOC.')
            return amoc
        elif method == 'field':
                moc = self._obj.MOC.isel(transport_reg=1,moc_comp=0).copy()
                moc.values[np.abs(moc.values) < 1e-6] = np.nan
                moc = moc.rename({'moc_z':'z_t', 
                                  'lat_aux_grid':'lat'})
                moc.name = 'amoc'
                return moc
        else:
            raise ValueError('method is not recognized, use [index, field]')

    @property
    def d18ow(self):
        d18ow = (self._obj.R18O - 1) * 1000
        d18ow = d18ow.rename('d18ow')
        d18ow.attrs['units'] = 'permil'
        return d18ow

    @property
    def ocnreg(self):
        return utl.region()

    @property
    def path(self):
        return self._obj.PA_P / self._obj.TH_P

    # convert depth unit to m
    def chdep(self):
        if self._obj.z_t[-1] > 1e5:
            self._obj['z_t'] /= 1e2
        else:
            pass
        return self._obj

    def _selbasin(self, grid='gx1v6', region='Atlantic'):
        basin = utl.ocean_region(grid)
        return self._obj.where(basin[region])

    def Atlantic(self, grid):
        return self._selbasin(grid, region='Atlantic')

    def Arc_Atlantic(self, grid):
        return self._selbasin(grid, region='Arc_Atlantic')

    def Pacific(self, grid):
        return self._selbasin(grid, region='Pacific')

    def Indo_Pacific(self, grid):
        return self._selbasin(grid, region='Indo_Pacific')

    def Pacific_LGM(self, grid):
        return self._selbasin(grid, region='Pacific_LGM')

    def Southern_Ocn(self, grid):
        return self._selbasin(grid, region='SouthernOcn')

    def North_Atlantic(self, grid):
        return self._selbasin(grid, region='North_Atlantic')

    # compute ocean heat transport
    def ocn_heat_transport(self, dlat=1, grid='g16'):

        from scipy import integrate
        # check time dimension
        if 'time' in self._obj.dims:
            flux = self._obj.SHF.mean('time')
        else:
            flux = self._obj.SHF

        area = dict(g16=utl.tarea_g16, g35=utl.tarea_g35, g37=utl.tarea_g37)
        flux_area = flux * area[grid] * 1e-4 # convert to m2
        #
        lat_bins = np.arange(-90,91,dlat)
        lat = np.arange(-89.5,90,dlat)

        if 'TLAT' in flux_area.coords.keys():
            flux_lat = flux_area.groupby_bins('TLAT', lat_bins, labels = lat).sum()
            latax = flux_lat.get_axis_num('TLAT_bins')
        elif 'ULAT' in flux_area.coords.keys():
            flux_lat = flux_area.groupby_bins('ULAT', lat_bins, labels = lat).sum()
            latax = flux_lat.get_axis_num('ULAT_bins')
        flux_lat.values = flux_lat - flux_lat.mean() # remove bias
        flux_lat.values = np.nan_to_num(flux_lat.values)
        integral = integrate.cumtrapz(flux_lat, x=None, initial=0., axis=latax)
        OHT = flux_lat.copy()
        OHT.values = integral *1e-15
        return OHT


    def mass_streamfun(self, dlat = 0.6, dlon = 0.1, OHT=False, region='global'):
        '''
        compute mass stream function in theta coordinates.
        reference to Ferrari and Ferreira 2011.
        '''
        dz = utl.dz_g16 * 1e-2 #convert to m
        angle = utl.angle_g16
        angle['ULONG'] = self._obj.ULONG # fix Ulong lost bug

        # meridional velocity
        VVEL = (self._obj.UVEL * np.sin(angle) + self._obj.VVEL * np.cos(angle)) * 1e-2 # convert to m

        # check region
        if region=='Global':
            T = self._obj.TEMP
        elif region == 'Indo_Pacific':
            VVEL = VVEL.utils.Indo_Pacific()
            T = self._obj.TEMP.utils.Indo_Pacific()
        elif region == 'Arc_Atlantic':
            VVEL = VVEL.utils.Arc_Atlantic()
            T = self._obj.TEMP.utils.Arc_Atlantic()
        else:
            raise ValueError('region is not supported.')

        T = T.utils.regrid(dlat=dlat, dlon=dlon)
        V = VVEL.utils.regrid(grid_style='U', dlat=dlat, dlon=dlon)

        # dxdz
        latrad = np.deg2rad(V.lat)
        lonrad = np.deg2rad(V.lon)
        dlon = lonrad[1] - lonrad[0]
        dx = cc.rearth * np.cos(latrad) * dlon # unit in m

        dzdx = dz * dx
        work = V * dzdx
#        work = work.fillna(0) # fill nan as 0
        Tmin = np.floor(T.min())
        Tmax = np.round(T.max())

        y = 0   # lat index
        k = 0   # theta index
        dt = 0.5    # theta resolution
        temp_range = np.arange(Tmin,Tmax,dt)
        Psi = np.zeros([len(work.lat),len(temp_range)])
        for t in temp_range:
            y = 0
            for l in work.lat:
                work1 = work.sel(lat=l).values
                Tsel = T.sel(lat=l).values
                if t <= np.nanmax(Tsel):
                    Psi[y, k] = np.nansum(work1[(Tsel>=np.nanmin(Tsel)) & (Tsel<=t)])
                else:
                    Psi[y, k] = np.NaN
                y += 1
            k += 1

        Psi = Psi * 1e-6 # convert to Sv
        Psi[Psi==0] = np.NaN
        Psi = -xr.DataArray(Psi, coords={'lat':work.lat, 'theta': temp_range},
                                dims=['lat', 'theta'])

        # smooth the stream function to remove noise
        Psi = Psi.rolling(lat=11, center=True).mean()
        Psi = Psi.rolling(theta=3, center=True).mean()

        if OHT:
            from scipy import integrate
            Psim3 = Psi * 1e6 # to m3/s
            Psim3 = Psim3.fillna(0)
            Psim3HT = Psim3 * cc.rhosw * cc.cpsw * 1e-15 # to PW
            theta_ax = Psim3HT.get_axis_num('theta')
            integral = integrate.cumtrapz(Psim3HT, x=Psim3HT.theta, initial=0., axis=theta_ax)
            OHT = xr.DataArray(integral, coords={'lat':Psi.lat, 'theta': temp_range},
                                        dims=['lat', 'theta'])
            return Psi.T, OHT.T
        else:
            return Psi.T


@xr.register_dataarray_accessor('utils')
class Utilities(object):
    def __init__(self, xarray_obj):
        self._obj = xarray_obj

    # regrid pop variables
    def regrid(self, dlon=1, dlat=1, grid_style='T'):
        import pyresample

        dims = self._obj.dims
        shape = self._obj.shape
        temp = self._obj.values
        temp = temp.reshape(-1,shape[-2],shape[-1])   # this requires time and z_t are at the first two axises
        temp = temp.transpose(1,2,0)    #lat, lon rightmost

        if grid_style is 'T':
            lon_curv = self._obj.TLONG.values.copy()
            lat_curv = self._obj.TLAT.values.copy()
        elif grid_style is 'U':
            lon_curv = self._obj.ULONG.values.copy()
            lat_curv = self._obj.ULAT.values.copy()

        # set lon to -180 to 180
        lon_curv[lon_curv>180] = lon_curv[lon_curv>180] - 360

        # targit grid
        lon = np.arange(-180.,179.01,dlon)
        lat = np.arange(-90.,89.999,dlat)
        lon_lin, lat_lin = np.meshgrid(lon,lat)
        lon_lin = pyresample.utils.wrap_longitudes(lon_lin)
        #define two grid systems
        orig_def = pyresample.geometry.SwathDefinition(lons=lon_curv, lats=lat_curv)
        targ_def = pyresample.geometry.SwathDefinition(lons=lon_lin, lats=lat_lin)
        rgd_data = pyresample.kd_tree.resample_nearest(orig_def, temp,
        targ_def, radius_of_influence=1000000*np.sqrt(dlon**2), fill_value=np.nan)

        rgd_data = rgd_data.transpose(2,0,1) #reshape back

        if len(dims) > 3:
            rgd_data = rgd_data.reshape(shape[0],shape[1],len(lat), len(lon))
            ds =  xr.DataArray(rgd_data, coords=[self._obj[dims[0]], self._obj[dims[1]], lat,lon],
                                dims=[dims[0], dims[1], 'lat', 'lon'])
            ds.name = self._obj.name
            # return ds

        elif len(dims) > 2:
            rgd_data = rgd_data.reshape(shape[0],len(lat), len(lon))
            ds = xr.DataArray(rgd_data, coords=[self._obj[dims[0]], lat,lon],
                                dims=[dims[0], 'lat', 'lon'])
            ds.name = self._obj.name
            # return ds
        
        elif len(dims) > 1:
            rgd_data = rgd_data.squeeze()
            ds = xr.DataArray(rgd_data, coords=[lat,lon], dims=['lat', 'lon'])
            ds.name = self._obj.name
            # return ds
        else:
            raise ValueError('Dataarray has more than 4 dimensions.')

        return ds

    def globalmean(self):
        lat_rad = xr.ufuncs.deg2rad(self._obj.lat)
        lat_cos = np.cos(lat_rad)
        if 'lon' in self._obj.dims:
            lonmn = self._obj.mean('lon')
            total = lonmn * lat_cos
        else:
            total = self._obj * lat_cos
        
        return total.sum("lat") / lat_cos.sum()

    def gbmeanpop(self, grid='g16'):

        if grid == 'g16':
            return self._obj
        if self._obj.size > 1e5:
            return self._obj / utl.tarea_g16.sum()

    def gbvolmean(self, grid='g16'):

        if grid == 'g16':
            vol = utl.dz_g16 * utl.tarea_g16
            total = self._obj * vol.values.reshape([-1,vol.shape])

        elif grid == 'g35':
            vol = utl.dz_g35 * utl.tarea_g35
            total = self._obj * vol
        elif grid == 'g37':
            vol = utl.dz_g37 * utl.tarea_g37
            total = self._obj * vol
        else:
            raise ValueError('Grid is not suppported.')

        if 'time' in self._obj.dims:
            output = total.groupby('time').sum() / vol.sum()
        else:
            output = total.sum() / vol.sum()

        output.name = self._obj.name
        return output

    def zonalmean(self, res=1):
        
        coords = list(self._obj.coords)
        
        if 'lon' in coords:
            return self._obj.mean('lon')
        
        if res == 1 :    
            lat_center = np.arange(-89.5, 90, 1)
            lat_bins = np.arange(-90, 91, 1)
        elif res == 3:
            lat_center = np.arange(-88.5, 90, 3)
            lat_bins = np.arange(-90, 91, 3)
        else: 
            lat_center = np.arange(-89.5, 90, 1)
            lat_bins = np.arange(-90, 91, 1)
        
        try:
            zonal = self._obj.groupby_bins('TLAT', lat_bins, labels=lat_center).mean('stacked_nlat_nlon') 
            zonal = zonal.rename({'TLAT_bins':'lat'})
        except:
            zonal = self._obj.groupby_bins('ULAT', lat_bins, labels=lat_center).mean('stacked_nlat_nlon')  
            zonal = zonal.rename({'ULAT_bins':'lat'})
    
        zonal.name = self._obj.name
        return zonal     
                
    def meridionalmean(self):

        lat_rad = np.deg2rad(self._obj.lat)
        coslat = np.cos(lat_rad)
        field = coslat * self._obj

        return field.sum() / coslat.sum()

    def selloc(self,loc='Green_land', grid_method='regular', mean_dim=['lat', 'lon']):

        if grid_method == 'regular':
            lat = self._obj.lat
            lon = self._obj.lon
        elif grid_method == 'T':
            lat = self._obj.TLAT
            lon = self._obj.TLONG
        elif grid_method == 'U':
            lat = self._obj.ULAT
            lon = self._obj.ULONG

#        if lon.max() > 180:
#            lon = lon[lon>180] - 180
        # later shall be wrapped into utils module
        loc = utl.locations[loc]
        sellect = self._obj.where((lat > loc[0]) & (lat < loc[1]) & (lon > loc[2])
                               & (lon < loc[3]), drop=True)
        s = sellect
        for d in mean_dim:
            sellect = sellect.mean(dim=d)

        sellect.attrs['Description'] = 'average data from lat: [' + str(s.lat.min().values.round(1)) + ', ' + str(s.lat.max().values.round(1)) + ']; ' + \
                                                    'from lon:[' + str(s.lon.min().values.round(1)) + ', ' + str(s.lon.max().values.round(1)) + '].'
        
        return sellect

    def _selbasin(self, grid='gx1v6', region='Atlantic'):
        basin = utl.ocean_region(grid)
        ds = self._obj.where(basin[region])
        ds.name = self._obj.name
        return ds

    def Atlantic(self, grid):
        return self._selbasin(grid, region='Atlantic')

    def Arc_Atlantic(self, grid):
        return self._selbasin(grid, region='Arc_Atlantic')

    def Pacific(self, grid):
        return self._selbasin(grid, region='Pacific')

    def Indo_Pacific(self, grid):
        return self._selbasin(grid, region='Indo_Pacific')

    def Pacific_LGM(self, grid):
        return self._selbasin(grid, region='Pacific_LGM')

    def Southern_Ocn(self, grid):
        return self._selbasin(grid, region='SouthernOcn')

    def North_Atlantic(self, grid):
        return self._selbasin(grid, region='North_Atlantic')


    # compute ocean heat transport
    def ocn_heat_transport(self, dlat=1, grid='g16', method='Flux_adjusted', lat_bd=90):

        from scipy import integrate

        flux = self._obj
        area = dict(g16=utl.tarea_g16, g35=utl.tarea_g35, g37=utl.tarea_g37)
        flux_area = flux.copy()
        flux_area.values = flux * area[grid] * 1e-4 # convert to m2

        lat_bins = np.arange(-90,91,dlat)
        lat = np.arange(-89.5,90,dlat)


        if 'TLAT' in flux_area.coords.keys():
            flux_lat = flux_area.groupby_bins('TLAT', lat_bins, labels = lat).sum('stacked_nlat_nlon')
            latax = flux_lat.get_axis_num('TLAT_bins')
        elif 'ULAT' in flux_area.coords.keys():
            flux_area = flux_area.rename({"ULAT":"TLAT"})
            flux_lat = flux_area.groupby_bins('TLAT', lat_bins, labels = lat).sum('stacked_nlat_nlon')
            latax = flux_lat.get_axis_num('TLAT_bins')

        TLAT_bins = flux_lat.TLAT_bins
        if method == "Flux_adjusted":

            flux_lat = flux_lat.where(TLAT_bins < lat_bd) # north bound
            flat_ave = flux_lat.mean('TLAT_bins')
            flux_lat.values = flux_lat - flat_ave # remove bias
            flux_lat = flux_lat.fillna(0)
            print("The ocean heat trasnport is computed by Flux adjustment.")

        elif method == "Flux":
            flux_lat = flux_lat.fillna(0)
            print("The ocean heat trasnport is computed by original flux.")
        else:
            raise ValueError("method is not suppoprted.")

        flux_lat.values = -np.flip(flux_lat.values, latax)   # integrate from north pole
        integral = integrate.cumtrapz(flux_lat, x=None, initial=0., axis=latax)
        OHT = flux_lat.copy()
        OHT["TLAT_bins"] = np.flip(flux_lat.TLAT_bins.values, 0)
        OHT.values = integral *1e-15

        return OHT


    def hybrid_to_pressure(self, model= 'CESM1', stride='m', P0=100000.):
        """
        Brought from darpy:https://github.com/darothen/darpy/blob/master/darpy/analysis.py
        Convert hybrid vertical coordinates to pressure coordinates
        corresponding to model sigma levels.
        Parameters
        ----------
        data : xarray.Dataset
            The dataset to inspect for computing vertical levels
        stride : str, either 'm' or 'i'
            Indicate if the field is on the model level interfaces or
            middles for referencing the correct hybrid scale coefficients
        P0 : float, default = 1000000.
            Default reference pressure in Pa, used as a fallback.
        """

        # A, B coefficients
        if model == 'CESM1':
            a = dict(i42=utl.hyai_cesm1_t42, m42=utl.hyam_cesm1_t42)
            b = dict(i42=utl.hybi_cesm1_t42, m42=utl.hybm_cesm1_t42)
        elif model == 'CCSM4' or model == 'CCSM3':
            a = dict(i42=utl.hyai_t42, m42=utl.hyam_t42)
            b = dict(i42=utl.hybi_t42, m42=utl.hybm_t42)

        if stride == 'm':
            a = a['m42']
            b = b['m42']
        else:
            a = a['i42']
            b = b['i42']

        P0_ref = P0
        PS = self._obj  # Surface pressure field

        pres_sigma = a*P0_ref + b*PS

        return pres_sigma

    def shuffle_dim(self, dim='lev'):

        data = self._obj
        ind_lev = data.get_axis_num('lev')
        dim = list(data.dims)
        dim.pop(ind_lev)
        dim_new = ['lev'] + dim
        data = data.transpose(*dim_new)
        return data

    def interp_to_pressure(self, coord_vals, new_coord_vals, interpolation='lin'):
        """
        browwed from darpy
        tested with NCL code.
        Interpolate all columns simultaneously by iterating over
        vertical dimension of original dataset, following methodology
        used in UV-CDAT.
        Parameters
        ----------
        data : xarray.DataArray
            The data (array) of values to be interpolated
        coord_vals : xarray.DataArray
            An array containing a 3D field to be used as an alternative vertical coordinate
        new_coord_vals : iterable
            New coordinate values to inerpolate to
        reverse_coord : logical, default=False
            Indicates that the coord *increases* from index 0 to n; should be "True" when
            interpolating pressure fields in CESM
        interpolation : str
            "log" or "lin", indicating the interpolation method
        Returns
        -------
        list of xarray.DataArrays of length equivalent to that of new_coord_vals, with the
        field interpolated to each value in new_coord_vals
        """

        # Shuffle dims so that 'lev' is first for simplicity
        data = self._obj
        data_orig_dim = list(data.dims)
        data = self.shuffle_dim(data)

        coords_out = {'lev': new_coord_vals}
        for c in data.dims:
            if c == 'lev':
                continue
            coords_out[c] = data.coords[c]


        # Find the 'lev' axis for interpolating
        orig_shape = data.shape
        axis = data.get_axis_num('lev')
        n_lev = orig_shape[axis]

        n_interp = len(new_coord_vals)  # Number of interpolant levels

        data_interp_shape = [n_interp, ] + list(orig_shape[1:])
        data_new = np.zeros(data_interp_shape)

        # Shape of array at any given level
        flat_shape = coord_vals.isel(lev=0).shape

        # Loop over the interpolant levels
        for ilev in range(n_interp):

            lev = new_coord_vals[ilev]

            P_abv = np.ones(flat_shape)
            # Array on level above, below
            A_abv, A_bel = -1.*P_abv, -1.*P_abv
            # Coordinate on level above, below
            P_abv, P_bel = -1.*P_abv, -1.*P_abv

            # Mask area where coordinate == levels
            P_eq = np.ma.masked_equal(P_abv, -1)

            # Loop from the second sigma level to the last one
            for i in range(1, n_lev):

                a = np.ma.greater_equal(coord_vals.isel(lev=i), lev)
                b = np.ma.less_equal(coord_vals.isel(lev=i - 1), lev)


                # Now, if the interpolant level is between the two
                # coordinate levels, then we can use these two levels for the
                # interpolation.
                a = (a & b)

                # Coordinate on level above, below
                P_abv = np.where(a, coord_vals[i], P_abv)
                P_bel = np.where(a, coord_vals[i - 1], P_bel)
                # Array on level above, below
                A_abv = np.where(a, data[i], A_abv)
                A_bel = np.where(a, data[i-1], A_bel)

                P_eq = np.where(coord_vals[i] == lev, data[i], P_eq)

            # If no data below, set to missing value; if there is, set to
            # (interpolating) level
            P_val = np.ma.masked_where((P_bel == -1), np.ones_like(P_bel)*lev)

            # Calculate interpolation
            if interpolation == 'log':
                tl = np.log(P_val/P_bel)/np.log(P_abv/P_bel)*(A_abv - A_bel) + A_bel
            elif interpolation == 'lin':
                tl = A_bel + (P_val-P_bel)*(A_abv - A_bel)/(P_abv - P_bel)
            else:
                raise ValueError("Don't know how to interpolate '{}'".format(interpolation))
            tl.fill_value = np.nan

            # Copy into result array, masking where values are missing
            # because of bad interpolation (out of bounds, etc.)
            tl[tl.mask] = np.nan
            data_new[ilev] = tl

        dataout = xr.DataArray(data_new, coords=coords_out, dims=data.dims)
        dataout = dataout.transpose(*data_orig_dim)
        return dataout


    def mass_streamfun(self):

        from scipy import integrate

        data = self._obj
#        lonlen = len(data.lon)
        if 'lon' in data.dims:
            data = data.fillna(0).mean('lon')
        levax = data.get_axis_num('lev')
        stream = integrate.cumtrapz(data * np.cos(np.deg2rad(data.lat)), x=data.lev * 1e2, initial=0., axis=levax)
        stream = stream * 2 * np.pi  / cc.g * cc.rearth * 1e-9
        stream = xr.DataArray(stream, coords=data.coords, dims=data.dims)
        stream = stream.rename('ovt')
        stream.attrs['long name'] = 'atmosphere overturning circulation'
        stream.attrs['unit'] = 'Sv (1e9 kg/s)'
        return stream

    def interp_lat(self, dlat=1):
        import re
        from scipy.interpolate import interp1d
        data = self._obj
        coords_name = list(data.dims)
        lat = []
        name = []
        for n in coords_name:
            name.append(n)
            if re.search('lat', n, re.IGNORECASE) is not None:
                lat.append(n)

        if len(lat) > 1:
            raise ValueError("datarray has more than one lat dim.")
        else:
            lat = lat.pop()

        latax = data.get_axis_num(lat)
        lat_out = np.arange(-89,90,dlat)
        fun = interp1d(data[lat], data.values, axis=latax, fill_value='extrapolate')
        data_out = fun(lat_out)

        # reconstruct it to dataarray
        name.pop(latax)
        coords_out = []
        dim = []
        for n in name:
            coords_out.append(data[n])
            dim.append(n)

        coords_out.insert(latax, lat_out)
        dim.insert(latax, 'lat')
        output = xr.DataArray(data_out, coords=coords_out, dims=dim)

        # get attributes back
        if data.name is not None:
            output = output.rename(data.name)

        return output

    def quickmap(self, ax=None, central_longitude=180, cmap='NCV_blu_red', **kwargs):

        import cartopy.crs as ccrs
        from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter

        if central_longitude == 180:
            xticks = [0, 60, 120, 180, 240, 300, 359.99]
        elif central_longitude == 0:
            xticks = [-180, -120, -60, 0, 60, 120, 180]
        else:
            central_longitude=180
            xticks = [0, 60, 120, 180, 240, 300, 359.99]
            print("didn't explicitly give center_lat, use 180 as defalut.")


        if ax is None:
            fig = plt.figure(figsize=(8.5,3.8))
            ax = fig.add_subplot(111, projection=ccrs.PlateCarree(central_longitude=central_longitude))

        cmaps = clrmp.cmap(cmap)
        self._obj.plot(ax=ax,cmap=cmaps,transform=ccrs.PlateCarree(), infer_intervals=True,
                       cbar_kwargs={'orientation': 'vertical',
                                    'fraction':0.09,
                                    'aspect':15}, **kwargs)

        #set other properties
        ax.set_global()
        ax.coastlines(linewidth=0.6)
        ax.set_xticks(xticks, crs=ccrs.PlateCarree())
        ax.set_yticks([-90, -60, -30, 0, 30, 60, 90], crs=ccrs.PlateCarree())
        lon_formatter = LongitudeFormatter(zero_direction_label=True,
                                           number_format='.0f')
        lat_formatter = LatitudeFormatter()
        ax.xaxis.set_major_formatter(lon_formatter)
        ax.yaxis.set_major_formatter(lat_formatter)
        ax.set_xlabel('')
        ax.set_ylabel('')
        return ax



@xr.register_dataarray_accessor('stat')
class Utilities(object):
    def __init__(self, xarray_obj):
        self._obj = xarray_obj

    def normalize(self, dim='time'):
        '''
        Normalize a series in dim
        '''

        dsarray = self._obj
        nm = x = dsarray - dsarray.mean(dim=dim)
        nm = nm / dsarray.std(dim=dim)
        try:
            nm.name = dsarray.name
            nm.attrs['Description'] = 'Normalized ' + dsarray.name + '.'
        except:
            pass
        return nm  


    def corr_with(self, dsarrayy, dim='time'):
        
        '''
        Pearson correlation
        '''
        dsarrayx = self._obj

        x = dsarrayx - dsarrayx.mean(dim=dim)
        y = dsarrayy - dsarrayy.mean(dim=dim)
        xy = x * y
        xy = xy.mean(dim=dim)

        xx = dsarrayx.std(dim=dim)
        yy = dsarrayy.std(dim=dim)
        r = xy / xx / yy
        r.name = 'r'
        r.attrs['units'] = 'unitless'
        try:
            r.attrs['Description'] = 'Pearson Correlation Coefficients between ' + dsarrayx.name + ' and ' + dsarrayy.name + '.'
        except:
            pass
        return r

    def regress_with(self, dsarrayy, dim='time'):
        
        '''
        Pearson correlation
        '''
        dsarrayx = self._obj

        x = dsarrayx - dsarrayx.mean(dim=dim)
        y = dsarrayy - dsarrayy.mean(dim=dim)
        xy = x * y
        xy = xy.mean(dim=dim)

        # xx = dsarrayx.std(dim=dim)
        yy = dsarrayy.std(dim=dim)
        r = xy / yy ** 2
        r.name = 'r'
        # r.attrs['units'] = 'unitless'
        try:
            r.attrs['Description'] = 'Regression Coefficients of ' + dsarrayx.name + ' on ' + dsarrayy.name + '.'
        except:
            pass
        return r

    
    def butter_filter(self, cutoff, fs, btype, order=5): 
        '''
        Butterworth filter, only applied on 1d array
        fs: sample rate
        '''
        from scipy import signal
        
        dsarray = self._obj

        nyq = 0.5 * fs
        # check if bandpass 
        if isinstance(cutoff, list) and 'band' in btype:
            normal_cutoff = [c / nyq for c in cutoff]
        else:
            normal_cutoff = cutoff / nyq

        b, a = signal.butter(order, normal_cutoff, btype=btype, analog=False)
        y = signal.filtfilt(b, a, dsarray.values)

        newds = xr.ones_like(dsarray)
        newds.values = y
        newds.attrs['Description'] = btype + ' Pass Butterworth filter at cutoff: ' + str(cutoff) 

        return newds



@xr.register_dataarray_accessor('plt')
class Utilities(object):
    def __init__(self, xarray_obj):
        self._obj = xarray_obj

    def quickmap(self, ax=None, central_longitude=180, cmap='NCV_blu_red', **kwargs):

        import cartopy.crs as ccrs
        from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter


        if central_longitude == 180:
            xticks = [0, 60, 120, 180, 240, 300, 359.99]
        elif central_longitude == 0:
            xticks = [-180, -120, -60, 0, 60, 120, 180]
        else:
            central_longitude=180
            xticks = [0, 60, 120, 180, 240, 300, 359.99]
            print("didn't explicitly give center_lat, use 180 as defalut.")


        if ax is None:
            fig = plt.figure(figsize=(8.5,3.8))
            ax = fig.add_subplot(111, projection=ccrs.PlateCarree(central_longitude=central_longitude))


        cmaps = clrmp.cmap(cmap)
        self._obj.plot(ax=ax,cmap=cmaps,transform=ccrs.PlateCarree(), infer_intervals=True,
                       cbar_kwargs={'orientation': 'vertical',
                                    'fraction':0.09,
                                    'aspect':15}, **kwargs)

        #set other properties
        ax.set_global()
        ax.coastlines(linewidth=0.6)
        ax.set_xticks(xticks, crs=ccrs.PlateCarree())
        ax.set_yticks([-90, -60, -30, 0, 30, 60, 90], crs=ccrs.PlateCarree())
        lon_formatter = LongitudeFormatter(zero_direction_label=True,
                                           number_format='.0f')
        lat_formatter = LatitudeFormatter()
        ax.xaxis.set_major_formatter(lon_formatter)
        ax.yaxis.set_major_formatter(lat_formatter)
        ax.set_xlabel('')
        ax.set_ylabel('')
        return ax
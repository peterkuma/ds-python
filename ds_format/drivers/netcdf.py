from netCDF4 import Dataset, num2date
import cftime
import numpy as np
import ds_format as ds
import datetime as dt
import aquarius_time as aq

def detect(filename):
	try:
		f = Dataset(filename)
		return True
	except:
		return False

def read_attrs(var):
	d = {}
	for name in var.ncattrs():
		d[name] = var.getncattr(name)
	return d

def read_var(f, name, sel=None, data=True):
	var = f[name]
	x = None
	attrs = read_attrs(var)
	dims = var.dimensions
	size = var.shape
	attrs.update({
		'.dims': dims,
		'.size': size,
	})
	if data:
		if sel:
			s = ds.misc.sel_slice(sel, dims)
			x = var[s]
		else:
			try:
				x = var[::] if data else None
			except ValueError:
				var.set_auto_mask(False)
				x = var[::] if data else None
	return [x, attrs]

def read(filename, variables=None, sel=None, full=False, jd=False):
	with Dataset(filename, 'r') as f:
		d = {}
		d['.'] = {}
		d['.']['.'] = read_attrs(f)
		for name in f.variables.keys():
			if variables is not None and name not in variables:
				if full:
					_, d['.'][name] = read_var(f, name, sel, False)
			else:
				d[name], d['.'][name] = read_var(f, name, sel)
	if jd:
		for name, data in d.iteritems():
			if name.startswith('.'): continue
			units = d['.'][name].get(u'units')
			calendar = d['.'][name].get(u'calendar')
			try:
				if calendar is not None:
					x = num2date(data, units=units, calendar=calendar)
				else:
					x = num2date(data, units=units)
			except: continue
			if len(x) == 0 or not isinstance(x[0], dt.datetime):
				continue
			d[name] = aq.from_datetime(list(x))
			d['.'][name]['units'] = 'days since -4712 12:00 UTC'
			d['.'][name]['units_comment'] = 'julian_date(utc)'
			if 'calendar' in d['.']:
				del d['.']['calendar']
	return d

def write(filename, d):
	with Dataset(filename, 'w') as f:
		dims = ds.get_dims(d)
		for k, v in dims.iteritems():
			f.createDimension(k, v)
		for name, data in d.iteritems():
			if name.startswith('.'):
				continue
			var = d['.'][name]
			if type(data) is not np.ndarray:
				data = np.array([data])
			v = f.createVariable(name, data.dtype, var['.dims'])
			v.setncatts({
				k: v
				for k, v in var.iteritems()
				if not k.startswith('.')
			})
			v[::] = data
		if '.' in d['.']:
			f.setncatts(d['.']['.'])

from_netcdf = read
to_netcdf = write


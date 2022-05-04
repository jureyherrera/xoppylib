import numpy
from xoppylib.xoppy_xraylib_util import descriptor_kind_index, density, reflectivity_fresnel
import xraylib # using: CS_Total_CP Refractive_Index_Re Refractive_Index_Im


def xpower_calc(energies=numpy.linspace(1000.0,50000.0,100), source=numpy.ones(100),
                substance=["Be"], flags=[0], dens=["?"], thick=[0.5], angle=[3.0], roughness=0.0,
                output_file=None):
    """
    Apply reflectivities/transmittivities of optical elements on a source spectrum

    :param energies: the array with photon energies in eV
    :param source: the spectral intensity or spectral power
    :param substance: a list with descriptors of each optical element  material
    :param flags: a list with 0 (filter or attenuator) or 1 (mirror) for all optical elements
    :param dens: a list with densities of o.e. materials. "?" is accepted for looking in the database
    :param thick: a list with the thickness in mm for all o.e.'s. Only applicable for filters
    :param angle: a list with the grazing angles in mrad for all o.e.'s. Only applicable for mirrors
    :param roughness:a list with the roughness RMS in A for all o.e.'s. Only applicable for mirrors
    :param output_file: name of the output file (default=None, no output file)
    :return: a dictionary with the results
    """


    nelem = len(substance)

    for i in range(nelem):
        kind = descriptor_kind_index(substance[i])
        if kind == -1:
            raise Exception("Bad descriptor/formula: %s"%substance[i])

        try:
            rho = float(dens[i])
        except:
            rho = density(substance[i])


        print("Density for %s: %g g/cm3"%(substance[i],rho))

        dens[i] = rho



    outArray = numpy.hstack( energies )
    outColTitles = ["Photon Energy [eV]"]
    outArray = numpy.vstack((outArray,source))
    outColTitles.append("Source")

    txt = ""
    txt += "*************************** power results ******************\n"
    if energies[0] != energies[-1]:
        txt += "  Source energy: start=%f eV, end=%f eV, points=%d \n"%(energies[0],energies[-1],energies.size)
    else:
        txt += "  Source energy: %f eV\n"%(energies[0])
    txt += "  Number of optical elements: %d\n"%(nelem)

    if energies[0] != energies[-1]:
        # I0 = source[0:-1].sum()*(energies[1]-energies[0])
        I0 = numpy.trapz(source, x=energies, axis=-1)
        txt += "  Incoming power (integral of spectrum): %f \n"%(I0)

        I1 = I0
    else:
        txt += "  Incoming power: %f \n"%(source[0])
        I0  = source[0]
        I1 = I0



    cumulated = source

    for i in range(nelem):
        #info oe
        if flags[i] == 0:
            txt += '      *****   oe '+str(i+1)+'  [Filter] *************\n'
            txt += '      Material: %s\n'%(substance[i])
            txt += '      Density [g/cm^3]: %f \n'%(dens[i])
            txt += '      thickness [mm] : %f \n'%(thick[i])
        else:
            txt += '      *****   oe '+str(i+1)+'  [Mirror] *************\n'
            txt += '      Material: %s\n'%(substance[i])
            txt += '      Density [g/cm^3]: %f \n'%(dens[i])
            txt += '      grazing angle [mrad]: %f \n'%(angle[i])
            txt += '      roughness [A]: %f \n'%(roughness[i])


        if flags[i] == 0: # filter
            tmp = numpy.zeros(energies.size)
            for j,energy in enumerate(energies):

                tmp[j] = xraylib.CS_Total_CP(substance[i],energy/1000.0)

            trans = numpy.exp(-tmp*dens[i]*(thick[i]/10.0))
            outArray = numpy.vstack((outArray,tmp))
            outColTitles.append("[oe %i] Total CS cm2/g"%(1+i))

            outArray = numpy.vstack((outArray,tmp*dens[i]))
            outColTitles.append("[oe %i] Mu cm^-1"%(1+i))


            outArray = numpy.vstack((outArray,trans))
            outColTitles.append("[oe %i] Transmitivity "% (1+i))

            outArray = numpy.vstack((outArray,1.0-trans))
            outColTitles.append("[oe %i] Absorption "% (1+i))

            absorbed = cumulated * (1.0-trans)
            cumulated *= trans

        if flags[i] == 1: # mirror
            tmp = numpy.zeros(energies.size)
            for j,energy in enumerate(energies):
                tmp[j] = xraylib.Refractive_Index_Re(substance[i],energy/1000.0,dens[i])
            delta = 1.0 - tmp
            outArray = numpy.vstack((outArray,delta))
            outColTitles.append("[oe %i] 1-Re[n]=delta"%(1+i))

            beta = numpy.zeros(energies.size)
            for j,energy in enumerate(energies):
                beta[j] = xraylib.Refractive_Index_Im(substance[i],energy/1000.0,dens[i])
            outArray = numpy.vstack((outArray,beta))
            outColTitles.append("[oe %i] Im[n]=beta"%(1+i))

            outArray = numpy.vstack((outArray,delta/beta))
            outColTitles.append("[oe %i] delta/beta"%(1+i))

            (rs,rp,runp) = reflectivity_fresnel(refraction_index_beta=beta,refraction_index_delta=delta,\
                                        grazing_angle_mrad=angle[i],roughness_rms_A=roughness[i],\
                                        photon_energy_ev=energies)
            outArray = numpy.vstack((outArray,rs))
            outColTitles.append("[oe %i] Reflectivity-s"%(1+i))

            outArray = numpy.vstack((outArray,1.0-rs))
            outColTitles.append("[oe %i] Transmitivity"%(1+i))

            absorbed = cumulated * (1.0 - rs)
            cumulated *= rs

        if energies[0] != energies[-1]:
            # I2 = cumulated[0:-1].sum()*(energies[1]-energies[0])
            #txt += "      Outcoming power [Sum]: %f\n"%(I2)
            #txt += "      Outcoming power [Trapez]: %f\n"%(I2b)
            I2 = numpy.trapz( cumulated, x=energies, axis=-1)
            txt += "      Outcoming power: %f\n"%(I2)
            txt += "      Absorbed power: %f\n"%(I1-I2)
            txt += "      Normalized Outcoming Power: %f\n"%(I2/I0)
            if flags[i] == 0:
                pass
                txt += "      Absorbed dose Gy.(mm^2 beam cross section)/s %f\n: "%((I1-I2)/(dens[i]*thick[i]*1e-6))
            I1 = I2
        else:
            I2 = cumulated[0]
            txt += "      Outcoming power: %f\n"%(cumulated[0])
            txt += "      Absorbed power: %f\n"%(I1-I2)
            txt += "      Normalized Outcoming Power: %f\n"%(I2/I0)
            I1 = I2

        outArray = numpy.vstack((outArray,absorbed))
        outColTitles.append("Spectral power absorbed in oe #%i"%(1+i))

        outArray = numpy.vstack((outArray,cumulated))
        outColTitles.append("Spectral power after oe #%i"%(1+i))

    ncol = len(outColTitles)
    npoints = energies.size

    if output_file is not None:
        f = open(output_file,"w")
        f.write("#F "+output_file+"\n")
        f.write("\n")
        f.write("#S 1 power: properties of optical elements\n")

        txt2 = txt.splitlines()
        for i in range(len(txt2)):
            f.write("#UINFO %s\n"%(txt2[i]))

        f.write("#N %d\n"%(ncol))
        f.write("#L")
        for i in range(ncol):
            f.write("  "+outColTitles[i])
        f.write("\n")

        for i in range(npoints):
                f.write((" %e "*ncol+"\n")%(tuple(outArray[:,i].tolist())))

        f.close()
        print("File written to disk: " + output_file)

    return {"data":outArray,"labels":outColTitles,"info":txt}

def xoppy_calc_xpower(
                      energies=numpy.linspace(1,100,100),
                      source    = numpy.ones(100),
                      substance = ['Si']*5,
                      thick     = [1.0]*5,
                      angle     = [0.0]*5,
                      dens      = ['?']*5,
                      roughness = [0.0]*5,
                      flags     = [1]*5,
                      NELEMENTS = 1,
                      FILE_DUMP = 0,
                      ):

    substance = substance[0:NELEMENTS+1]
    thick     = thick[0:NELEMENTS+1]
    angle     = angle[0:NELEMENTS+1]
    dens      = dens[0:NELEMENTS+1]
    roughness = roughness[0:NELEMENTS+1]
    flags     = flags[0:NELEMENTS+1]


    if FILE_DUMP:
        output_file = "power.spec"
    else:
        output_file = None

    out_dictionary = xpower_calc(energies=energies,source=source,substance=substance,
                                 flags=flags,dens=dens,thick=thick,angle=angle,roughness=roughness,output_file=output_file)

    return out_dictionary

if __name__ == "__main__":
    print(xoppy_calc_xpower())